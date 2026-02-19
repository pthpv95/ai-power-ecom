"""
Conversation persistence — save and load messages from PostgreSQL.

This is the backbone of multi-turn memory. Every message (user and assistant)
gets stored with a conversation_id so we can reconstruct the full history
on the next request.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message


async def save_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
) -> Message:
    """Save a single message to the database."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    db.add(message)
    await db.commit()
    return message


async def load_messages(
    db: AsyncSession,
    conversation_id: str,
) -> list[Message]:
    """Load all messages for a conversation, ordered by creation time."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()
