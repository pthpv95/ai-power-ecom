import asyncio
import json
import logging
import uuid

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.agent.graph import agent
from app.agent.context import db_var, user_id_var
from app.redis_client import get_redis
from app.services.conversation import save_message, load_messages
from app.services.context_manager import build_context
from app.schemas import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_MESSAGE_LENGTH = 2000       # characters, reject input over this
SSE_TIMEOUT_SECONDS = 60        # close SSE if no events for this long
SSE_KEEPALIVE_SECONDS = 15      # send heartbeat comment to prevent proxy timeouts


class ChatRequest(BaseModel):
    user_id: str
    message: str
    conversation_id: str | None = None


class EnqueueResponse(BaseModel):
    conversation_id: str
    status: str


def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _stream_key(conversation_id: str) -> str:
    return f"stream:{conversation_id}"


def _arq_redis_settings() -> RedisSettings:
    """Convert redis_url string to arq's RedisSettings."""
    from urllib.parse import urlparse
    parsed = urlparse(settings.redis_url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


# Lazy-initialized Arq connection pool (shared across requests)
_arq_pool = None


async def _get_arq_pool():
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(_arq_redis_settings())
    return _arq_pool


# ── POST /stream — enqueue the agent task, return immediately ────────────────

@router.post("/stream", response_model=EnqueueResponse)
async def chat_stream(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Enqueue the agent task and return the conversation_id.

    The client should then connect to GET /events/{conversation_id}
    to receive SSE events (status, token, cart_updated, done).
    """
    if len(body.message) > MAX_MESSAGE_LENGTH:
        return JSONResponse(
            status_code=400,
            content={"detail": "Message exceeds 2000 character limit."},
        )

    conversation_id = body.conversation_id or str(uuid.uuid4())

    # Save user message to DB
    await save_message(db, conversation_id, "user", body.message)

    # Enqueue the agent task — _job_id prevents duplicate processing
    pool = await _get_arq_pool()
    await pool.enqueue_job(
        "run_agent_task",
        conversation_id=conversation_id,
        user_id=body.user_id,
        _job_id=conversation_id,
    )

    return EnqueueResponse(conversation_id=conversation_id, status="queued")


# ── GET /events/{conversation_id} — SSE reader from Redis Stream ─────────────

@router.get("/events/{conversation_id}")
async def chat_events(
    conversation_id: str,
    last_id: str = Query(default="0-0", description="Resume from this Redis Stream ID"),
):
    """
    SSE endpoint that reads events from the Redis Stream published
    by the Arq worker. Supports reconnect via ?last_id= query param.
    """
    async def event_stream():
        redis = get_redis()
        stream = _stream_key(conversation_id)
        cursor = last_id
        idle_intervals = 0
        max_idle = SSE_TIMEOUT_SECONDS // SSE_KEEPALIVE_SECONDS

        while True:
            # Block for keepalive interval — short enough to send heartbeats
            result = await redis.xread(
                {stream: cursor},
                count=50,
                block=SSE_KEEPALIVE_SECONDS * 1000,
            )

            if not result:
                idle_intervals += 1
                if idle_intervals >= max_idle:
                    # Total timeout reached — no events for SSE_TIMEOUT_SECONDS
                    yield sse_event({
                        "type": "error",
                        "content": "Stream timed out. Please try again.",
                    })
                    return
                # Send SSE comment as keepalive (prevents proxy/browser timeout)
                yield ":keepalive\n\n"
                continue

            idle_intervals = 0  # reset on activity

            for _stream_name, messages in result:
                for msg_id, fields in messages:
                    cursor = msg_id
                    data = json.loads(fields["data"])
                    yield sse_event(data)

                    # Close after "done" or "error" event
                    if data.get("type") in ("done", "error"):
                        return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Load conversation history ─────────────────────────────────────────────────

@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(conversation_id: str, db: AsyncSession = Depends(get_db)):
    messages = await load_messages(db, conversation_id)
    return messages


# ── Non-streaming endpoint for Swagger testing ───────────────────────────────

class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    db_var.set(db)
    user_id_var.set(body.user_id)

    conversation_id = body.conversation_id or str(uuid.uuid4())
    await save_message(db, conversation_id, "user", body.message)

    db_messages = await load_messages(db, conversation_id)
    messages = await build_context(db_messages)

    langsmith_config = {
        "metadata": {
            "conversation_id": conversation_id,
            "user_id": body.user_id,
        },
        "tags": [f"conv:{conversation_id}"],
    }

    result = await agent.ainvoke({"messages": messages}, config=langsmith_config)
    ai_message = result["messages"][-1]

    await save_message(db, conversation_id, "assistant", ai_message.content)
    return ChatResponse(reply=ai_message.content, conversation_id=conversation_id)
