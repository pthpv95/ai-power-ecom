from decimal import Decimal
from unittest.mock import patch

from app.models import MemoryCategory, UserMemory
from app.services.memory_recall import build_memory_context_block, load_user_memories


async def test_load_user_memories_orders_by_confidence_desc(db):
    db.add_all(
        [
            UserMemory(
                user_id="recall-user",
                category=MemoryCategory.BRAND,
                key="jackets",
                value="Patagonia",
                confidence=Decimal("0.90"),
            ),
            UserMemory(
                user_id="recall-user",
                category=MemoryCategory.BUDGET,
                key="boots",
                value="under $150",
                confidence=Decimal("0.60"),
            ),
        ]
    )
    await db.commit()

    memories = await load_user_memories(db, "recall-user", max_tokens=None)

    assert [memory.key for memory in memories] == ["jackets", "boots"]


async def test_load_user_memories_respects_token_cap(db):
    db.add_all(
        [
            UserMemory(
                user_id="recall-cap",
                category=MemoryCategory.BRAND,
                key="jackets",
                value="Patagonia",
                confidence=Decimal("0.90"),
            ),
            UserMemory(
                user_id="recall-cap",
                category=MemoryCategory.SIZE,
                key="boots",
                value="11",
                confidence=Decimal("0.80"),
            ),
            UserMemory(
                user_id="recall-cap",
                category=MemoryCategory.STYLE,
                key="rain gear",
                value="minimalist",
                confidence=Decimal("0.70"),
            ),
        ]
    )
    await db.commit()

    with patch(
        "app.services.memory_recall.count_text_tokens",
        side_effect=lambda text: len(text),
    ):
        memories = await load_user_memories(db, "recall-cap", max_tokens=120)

    assert [memory.key for memory in memories] == ["jackets", "boots"]


async def test_build_memory_context_block_empty_when_no_memories(db):
    block = await build_memory_context_block(db, "new-user")
    assert block == ""
