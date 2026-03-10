from decimal import Decimal

from sqlalchemy import select

from app.agent.context import db_var, user_id_var
from app.agent.tools import get_user_preferences, manage_memory
from app.models import MemoryCategory, UserMemory


def setup_context(db, user_id="test_user"):
    db_var.set(db)
    user_id_var.set(user_id)


async def test_get_user_preferences_returns_grouped_preferences(db):
    setup_context(db, "prefs-user")
    db.add_all(
        [
            UserMemory(
                user_id="prefs-user",
                category=MemoryCategory.BRAND,
                key="jackets",
                value="Patagonia",
                confidence=Decimal("0.90"),
            ),
            UserMemory(
                user_id="prefs-user",
                category=MemoryCategory.SIZE,
                key="hiking boots",
                value="10",
                confidence=Decimal("0.80"),
            ),
        ]
    )
    await db.commit()

    result = await get_user_preferences.ainvoke({})

    assert "brand" in result
    assert "jackets: Patagonia" in result
    assert "size" in result
    assert "hiking boots: 10" in result


async def test_manage_memory_updates_existing_preference(db):
    setup_context(db, "prefs-user")
    db.add(
        UserMemory(
            user_id="prefs-user",
            category=MemoryCategory.SIZE,
            key="hiking boots",
            value="10",
            confidence=Decimal("0.70"),
        )
    )
    await db.commit()

    result = await manage_memory.ainvoke(
        {"action": "update", "category": "size", "key": "hiking boots", "value": "11"}
    )

    assert "Updated stored preference" in result

    stored = await db.execute(
        select(UserMemory).where(
            UserMemory.user_id == "prefs-user",
            UserMemory.category == MemoryCategory.SIZE,
            UserMemory.key == "hiking boots",
        )
    )
    assert stored.scalar_one().value == "11"


async def test_manage_memory_deletes_preference(db):
    setup_context(db, "prefs-user")
    db.add(
        UserMemory(
            user_id="prefs-user",
            category=MemoryCategory.BRAND,
            key="jackets",
            value="Patagonia",
            confidence=Decimal("0.70"),
        )
    )
    await db.commit()

    result = await manage_memory.ainvoke(
        {"action": "delete", "category": "brand", "key": "jackets"}
    )

    assert "Deleted stored preference" in result

    stored = await db.execute(
        select(UserMemory).where(
            UserMemory.user_id == "prefs-user",
            UserMemory.category == MemoryCategory.BRAND,
            UserMemory.key == "jackets",
        )
    )
    assert stored.scalar_one_or_none() is None
