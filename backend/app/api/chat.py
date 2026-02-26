import json
import logging
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.database import get_db
from app.agent.graph import agent, SYSTEM_PROMPT, TOOL_MAP, llm_with_tools
from app.agent.context import db_var, user_id_var
from app.services.conversation import save_message, load_messages
from app.services.context_manager import build_context
from app.schemas import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Guardrails ────────────────────────────────────────────────────────────────
# Prevent runaway agent loops. If the agent calls more tools than this in a
# single user turn, something is wrong — bail out gracefully.
MAX_TOOL_ROUNDS = 5
MAX_MESSAGE_LENGTH = 2000  # characters, reject input over this


class ChatRequest(BaseModel):
    user_id: str
    message: str
    conversation_id: str | None = None


FRIENDLY_NAMES = {
    "search_products": "Searching products...",
    "get_product_details": "Getting product details...",
    "add_to_cart": "Adding to cart...",
    "remove_from_cart": "Removing from cart...",
    "get_current_cart": "Checking your cart...",
    "compare_products": "Comparing products...",
}


def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/stream")
async def chat_stream(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Input validation
    if len(body.message) > MAX_MESSAGE_LENGTH:
        async def reject():
            yield sse_event({"type": "token", "content": "Your message is too long. Please keep it under 2000 characters."})
            yield sse_event({"type": "done", "conversation_id": body.conversation_id or ""})
        return StreamingResponse(reject(), media_type="text/event-stream")

    db_var.set(db)
    user_id_var.set(body.user_id)

    conversation_id = body.conversation_id or str(uuid.uuid4())
    await save_message(db, conversation_id, "user", body.message)

    db_messages = await load_messages(db, conversation_id)
    messages = await build_context(db_messages)

    async def event_generator():
        current_messages = list(messages)
        if not any(isinstance(m, SystemMessage) for m in current_messages):
            current_messages = [SystemMessage(content=SYSTEM_PROMPT)] + current_messages

        # LangSmith metadata — filter traces by conversation_id or user_id
        langsmith_config = {
            "metadata": {
                "conversation_id": conversation_id,
                "user_id": body.user_id,
            },
            "tags": [f"conv:{conversation_id}"],
        }

        full_response = ""
        tool_rounds = 0

        try:
            while True:
                response = await llm_with_tools.ainvoke(
                    current_messages, config=langsmith_config
                )

                if response.tool_calls:
                    tool_rounds += 1

                    # Guardrail: prevent infinite tool loops
                    if tool_rounds > MAX_TOOL_ROUNDS:
                        logger.warning(
                            f"Agent exceeded {MAX_TOOL_ROUNDS} tool rounds for conversation {conversation_id}"
                        )
                        full_response = "I got a bit lost processing your request. Could you try rephrasing?"
                        yield sse_event({"type": "status", "content": ""})
                        yield sse_event({"type": "token", "content": full_response})
                        break

                    # Append AIMessage ONCE before processing its tool calls
                    current_messages.append(response)

                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        yield sse_event({
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
                            yield sse_event({"type": "cart_updated"})

                        current_messages.append(ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call["id"],
                            name=tool_call["name"],
                        ))

                    continue

                else:
                    yield sse_event({"type": "status", "content": ""})

                    async for chunk in llm_with_tools.astream(
                        current_messages, config=langsmith_config
                    ):
                        token = chunk.content
                        if token:
                            full_response += token
                            yield sse_event({"type": "token", "content": token})

                    break

        except Exception as e:
            logger.error(f"Agent error for conversation {conversation_id}: {e}")
            full_response = "Sorry, I encountered an error. Please try again in a moment."
            yield sse_event({"type": "status", "content": ""})
            yield sse_event({"type": "token", "content": full_response})

        await save_message(db, conversation_id, "assistant", full_response)
        yield sse_event({"type": "done", "conversation_id": conversation_id})

    return StreamingResponse(
        event_generator(),
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
