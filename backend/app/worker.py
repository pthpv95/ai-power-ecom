"""
Arq worker — runs the agent loop outside the HTTP request handler.

The API server enqueues a job; this worker picks it up, runs the full
LLM + tool-call loop, and publishes each event to a Redis Stream so
the SSE endpoint can relay them to the client.

Start with:  uv run arq app.worker.WorkerSettings
"""
import json
import logging

from arq.connections import RedisSettings
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from app.agent.context import db_var, user_id_var
from app.agent.graph import TOOL_MAP, compose_system_prompt, llm_with_tools
from app.config import settings
from app.database import SessionLocal
from app.redis_client import get_redis
from app.services.context_manager import build_context_with_reserved_tokens
from app.services.conversation import load_messages, save_message
from app.services.memory_extractor import extract_and_store_memories
from app.services.memory_recall import build_memory_context_block, count_text_tokens

logger = logging.getLogger(__name__)

# ── Guardrails (same as chat.py) ─────────────────────────────────────────────
MAX_TOOL_ROUNDS = 5
STREAM_TTL_SECONDS = 3600  # auto-cleanup Redis streams after 1 hour

FRIENDLY_NAMES = {
    "search_products": "Searching products...",
    "get_product_details": "Getting product details...",
    "add_to_cart": "Adding to cart...",
    "remove_from_cart": "Removing from cart...",
    "get_current_cart": "Checking your cart...",
    "compare_products": "Comparing products...",
    "get_user_preferences": "Checking your saved preferences...",
    "manage_memory": "Updating your saved preferences...",
}


def _stream_key(request_id: str) -> str:
    """Redis Stream key — unique per user message (not per conversation)."""
    return f"stream:{request_id}"


async def _publish(redis, request_id: str, event: dict) -> None:
    """Append an event to the request's Redis Stream."""
    await redis.xadd(
        _stream_key(request_id),
        {"data": json.dumps(event)},
    )


async def run_agent_task(ctx: dict, *, conversation_id: str, user_id: str, request_id: str) -> None:
    """
    Core agent loop — extracted from chat.py's event_generator().

    Publishes SSE-compatible events to a Redis Stream:
      - {"type": "status", "content": "Searching products..."}
      - {"type": "token", "content": "Here are some..."}
      - {"type": "cart_updated"}
      - {"type": "done", "conversation_id": "..."}
      - {"type": "error", "content": "..."}   (on failure)
    """
    redis = get_redis()

    # Worker manages its own DB session (not FastAPI's Depends(get_db))
    async with SessionLocal() as db:
        db_var.set(db)
        user_id_var.set(user_id)

        try:
            db_messages = await load_messages(db, conversation_id)
            memory_block = await build_memory_context_block(db, user_id)
            memory_tokens = count_text_tokens(memory_block) if memory_block else 0
            messages = await build_context_with_reserved_tokens(
                db_messages,
                reserved_tokens=memory_tokens,
            )

            current_messages = list(messages)
            if not any(isinstance(m, SystemMessage) for m in current_messages):
                current_messages = [SystemMessage(content=compose_system_prompt(memory_block))] + current_messages

            langsmith_config = {
                "metadata": {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                },
                "tags": [f"conv:{conversation_id}"],
            }

            full_response = ""
            tool_rounds = 0

            while True:
                response = await llm_with_tools.ainvoke(
                    current_messages, config=langsmith_config
                )

                if response.tool_calls:
                    tool_rounds += 1

                    if tool_rounds > MAX_TOOL_ROUNDS:
                        logger.warning(
                            f"Agent exceeded {MAX_TOOL_ROUNDS} tool rounds "
                            f"for conversation {conversation_id}"
                        )
                        full_response = (
                            "I got a bit lost processing your request. "
                            "Could you try rephrasing?"
                        )
                        await _publish(redis, request_id, {"type": "status", "content": ""})
                        await _publish(redis, request_id, {"type": "token", "content": full_response})
                        break

                    current_messages.append(response)

                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        await _publish(redis, request_id, {
                            "type": "status",
                            "content": FRIENDLY_NAMES.get(tool_name, f"Running {tool_name}..."),
                        })

                        try:
                            tool_fn = TOOL_MAP[tool_call["name"]]
                            result = await tool_fn.ainvoke(tool_call["args"])
                        except Exception as e:
                            logger.error(f"Tool {tool_name} failed: {e}")
                            result = f"Tool error: unable to complete {tool_name}. Please try again."

                        if tool_name in ("add_to_cart", "remove_from_cart", "clear_cart"):
                            await _publish(redis, request_id, {"type": "cart_updated"})

                        current_messages.append(ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call["id"],
                            name=tool_call["name"],
                        ))

                    continue

                else:
                    await _publish(redis, request_id, {"type": "status", "content": ""})

                    async for chunk in llm_with_tools.astream(
                        current_messages, config=langsmith_config
                    ):
                        token = chunk.content
                        if token:
                            full_response += token
                            await _publish(redis, request_id, {"type": "token", "content": token})

                    break
            assistant_message = await save_message(
                db,
                conversation_id,
                "assistant",
                full_response,
                user_id=user_id,
            )

            try:
                source_message_id = next(
                    (message.id for message in reversed(db_messages) if message.role == "user"),
                    None,
                )
                extraction_messages = [
                    message for message in current_messages if not isinstance(message, SystemMessage)
                ]
                extraction_messages.append(AIMessage(content=full_response))
                await extract_and_store_memories(
                    db,
                    user_id,
                    extraction_messages,
                    source_message_id=source_message_id or assistant_message.id,
                )
            except Exception:
                logger.exception(
                    "Memory extraction failed for conversation %s",
                    conversation_id,
                )

        except Exception as e:
            logger.error(f"Worker error for conversation {conversation_id}: {e}")
            await _publish(redis, request_id, {
                "type": "error",
                "content": "Sorry, I encountered an error. Please try again in a moment.",
            })

        # Always emit "done" so the SSE reader knows to close
        await _publish(redis, request_id, {
            "type": "done",
            "conversation_id": conversation_id,
        })

        # Auto-cleanup: expire the stream after 1 hour
        await redis.expire(_stream_key(request_id), STREAM_TTL_SECONDS)


# ── Arq WorkerSettings ───────────────────────────────────────────────────────

def _parse_redis_settings() -> RedisSettings:
    """Convert redis_url string to arq's RedisSettings."""
    from urllib.parse import urlparse
    parsed = urlparse(settings.redis_url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


class WorkerSettings:
    functions = [run_agent_task]
    redis_settings = _parse_redis_settings()
    max_jobs = 10
    job_timeout = 120       # seconds — generous for multi-tool agent loops
    retry_jobs = True       # allow retries for transient failures
    max_tries = 2           # original + 1 retry
