from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, AIMessage

from app.database import get_db
from app.agent.graph import agent
from app.agent.context import db_var, user_id_var

router = APIRouter()


class ChatMessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: list[ChatMessageIn] = []


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Set context vars — tools read from these
    db_var.set(db)
    user_id_var.set(body.user_id)

    # Convert frontend history to LangChain messages
    messages = []
    for msg in body.history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))

    messages.append(HumanMessage(content=body.message))

    # Run the agent
    result = await agent.ainvoke({"messages": messages})

    ai_message = result["messages"][-1]
    return ChatResponse(reply=ai_message.content)
