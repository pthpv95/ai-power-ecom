from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def ensure_user_exists(db: AsyncSession, user_id: str) -> User:
    """Create a user record if it doesn't already exist (lazy upsert)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(id=user_id)
        db.add(user)
        await db.flush()
    return user
