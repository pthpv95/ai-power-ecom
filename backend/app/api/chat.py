import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

from app.database import get_db
from app.agent.graph import agent
from app.agent.context import db_var, user_id_var
from app.services.conversation import save_message, load_messages
from app.services.context_manager import build_context

router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str
    message: str
    conversation_id: str | None = None  # None = start new conversation


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str  # return it so frontend can send it back next time


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Set context vars for tools
    db_var.set(db)
    user_id_var.set(body.user_id)

    # Generate conversation_id if new conversation
    conversation_id = body.conversation_id or str(uuid.uuid4())

    # Save the user's message to DB
    await save_message(db, conversation_id, "user", body.message)

    # Load full conversation history from DB
    db_messages = await load_messages(db, conversation_id)

    # Build context: recent messages verbatim, older ones summarized
    messages = await build_context(db_messages)

    # If build_context returned a summary + recent, the current user message
    # is already in there. If not, we still have it from db_messages.
    # Either way, messages now contains the right context.

    # Run the agent
    result = await agent.ainvoke({"messages": messages})

    # Extract the final AI response
    ai_message = result["messages"][-1]

    # Save the assistant's reply to DB
    await save_message(db, conversation_id, "assistant", ai_message.content)

    return ChatResponse(reply=ai_message.content, conversation_id=conversation_id)
