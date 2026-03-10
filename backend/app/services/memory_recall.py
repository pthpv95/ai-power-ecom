from collections import defaultdict

import tiktoken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MemoryCategory, UserMemory

MEMORY_TOKEN_LIMIT = 500
ENCODER = tiktoken.encoding_for_model("gpt-4o")


def count_text_tokens(text: str) -> int:
    return len(ENCODER.encode(text))


async def load_user_memories(
    db: AsyncSession,
    user_id: str,
    *,
    category: str | MemoryCategory | None = None,
    max_tokens: int | None = MEMORY_TOKEN_LIMIT,
) -> list[UserMemory]:
    stmt = select(UserMemory).where(UserMemory.user_id == user_id)

    if category is not None:
        stmt = stmt.where(UserMemory.category == _normalize_category_filter(category))

    stmt = stmt.order_by(UserMemory.confidence.desc(), UserMemory.updated_at.desc(), UserMemory.id.desc())

    result = await db.execute(stmt)
    memories = list(result.scalars().all())
    if max_tokens is None:
        return memories
    return cap_memories_by_tokens(memories, max_tokens=max_tokens)


def cap_memories_by_tokens(memories: list[UserMemory], *, max_tokens: int) -> list[UserMemory]:
    selected: list[UserMemory] = []
    for memory in memories:
        candidate = selected + [memory]
        if count_text_tokens("Known user preferences:\n" + format_memories(candidate)) > max_tokens:
            break
        selected = candidate
    return selected


async def build_memory_context_block(db: AsyncSession, user_id: str, *, max_tokens: int = MEMORY_TOKEN_LIMIT) -> str:
    memories = await load_user_memories(db, user_id, max_tokens=max_tokens)
    if not memories:
        return ""
    return "Known user preferences:\n" + format_memories(memories)


def format_memories(memories: list[UserMemory]) -> str:
    grouped: dict[str, list[UserMemory]] = defaultdict(list)
    for memory in memories:
        grouped[memory.category.value].append(memory)

    lines: list[str] = []
    for category in sorted(grouped.keys()):
        lines.append(f"- {category}:")
        for memory in grouped[category]:
            lines.append(f"  - {memory.key}: {memory.value} (confidence {float(memory.confidence):.2f})")
    return "\n".join(lines)


def format_memory_line(memory: UserMemory) -> str:
    return f"{memory.category.value} {memory.key} {memory.value} confidence {float(memory.confidence):.2f}"


def _normalize_category_filter(category: str | MemoryCategory) -> MemoryCategory:
    if isinstance(category, MemoryCategory):
        return category
    return MemoryCategory(str(category).lower())
