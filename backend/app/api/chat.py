import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.database import get_db
from app.agent.graph import agent, SYSTEM_PROMPT, TOOL_MAP, llm_with_tools
from app.agent.context import db_var, user_id_var
from app.services.conversation import save_message, load_messages
from app.services.context_manager import build_context

router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str
    message: str
    conversation_id: str | None = None


def sse_event(data: dict) -> str:
    """Format a dict as an SSE event string."""
    return f"data: {json.dumps(data)}\n\n"


@router.post("/stream")
async def chat_stream(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    SSE streaming endpoint.

    Streams three types of events to the frontend:
      - status:  tool execution updates ("Searching products...")
      - token:   individual tokens as GPT-4o generates them
      - done:    signals the stream is complete, includes conversation_id

    The frontend reads these with fetch() + ReadableStream.
    We use POST (not GET) because we need to send a request body.
    """
    db_var.set(db)
    user_id_var.set(body.user_id)

    conversation_id = body.conversation_id or str(uuid.uuid4())
    await save_message(db, conversation_id, "user", body.message)

    db_messages = await load_messages(db, conversation_id)
    messages = await build_context(db_messages)

    async def event_generator():
        """
        Runs the agent loop manually (instead of agent.ainvoke) so we can
        stream tokens from the final response and emit status events
        when tools are called.

        This is the same agent_node → tool_node → agent_node loop,
        but we control each step to intercept events.
        """
        # Prepend system prompt
        current_messages = list(messages)
        if not any(isinstance(m, SystemMessage) for m in current_messages):
            current_messages = [SystemMessage(content=SYSTEM_PROMPT)] + current_messages

        full_response = ""

        while True:
            # Check if this is the final turn (no tool calls expected)
            # First, do a non-streaming call to check for tool calls
            response = await llm_with_tools.ainvoke(current_messages)

            if response.tool_calls:
                # Agent wants to call tools — execute them
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    # Emit status event
                    friendly_names = {
                        "search_products": "Searching products...",
                        "get_product_details": "Getting product details...",
                        "add_to_cart": "Adding to cart...",
                        "remove_from_cart": "Removing from cart...",
                        "get_current_cart": "Checking your cart...",
                        "compare_products": "Comparing products...",
                    }
                    yield sse_event({
                        "type": "status",
                        "content": friendly_names.get(tool_name, f"Running {tool_name}..."),
                    })

                    tool_fn = TOOL_MAP[tool_call["name"]]
                    result = await tool_fn.ainvoke(tool_call["args"])

                    from langchain_core.messages import ToolMessage
                    current_messages.append(response)
                    current_messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"],
                        name=tool_call["name"],
                    ))

                # Loop back — agent sees tool results and decides next step
                continue

            else:
                # No tool calls — this is the final response. Stream it token by token.
                yield sse_event({"type": "status", "content": ""})  # clear status

                async for chunk in llm_with_tools.astream(current_messages):
                    token = chunk.content
                    if token:
                        full_response += token
                        yield sse_event({"type": "token", "content": token})

                break

        # Save the complete response to DB
        await save_message(db, conversation_id, "assistant", full_response)

        yield sse_event({"type": "done", "conversation_id": conversation_id})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering if behind proxy
        },
    )


# Keep the non-streaming endpoint for Swagger testing
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

    result = await agent.ainvoke({"messages": messages})
    ai_message = result["messages"][-1]

    await save_message(db, conversation_id, "assistant", ai_message.content)
    return ChatResponse(reply=ai_message.content, conversation_id=conversation_id)
