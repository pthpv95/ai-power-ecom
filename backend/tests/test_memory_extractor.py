from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlalchemy import select

from app.models import MemoryCategory, UserMemory
from app.services.memory_extractor import (
    ExtractedMemory,
    extract_and_store_memories,
    extract_preference_facts,
    normalize_memory_category,
    parse_extracted_memories,
    should_extract_memories,
)


def test_parse_extracted_memories_handles_json_code_fence():
    payload = """```json
    [
      {"category": "brand", "key": "jackets", "value": "Patagonia"},
      {"category": "price", "key": "boots", "value": "under $150"}
    ]
    ```"""

    memories = parse_extracted_memories(payload)

    assert memories == [
        ExtractedMemory(category=MemoryCategory.BRAND, key="jackets", value="Patagonia"),
        ExtractedMemory(category=MemoryCategory.BUDGET, key="boots", value="under $150"),
    ]


def test_normalize_memory_category_maps_aliases():
    assert normalize_memory_category("brands") == MemoryCategory.BRAND
    assert normalize_memory_category("price") == MemoryCategory.BUDGET
    assert normalize_memory_category("aesthetic") == MemoryCategory.STYLE
    assert normalize_memory_category("something-else") == MemoryCategory.OTHER


def test_should_extract_memories_skips_non_product_chat():
    messages = [
        HumanMessage(content="hello"),
        AIMessage(content="Hi there, how can I help?"),
    ]

    assert should_extract_memories(messages) is False


def test_should_extract_memories_detects_tool_signals():
    messages = [
        HumanMessage(content="Show me jackets"),
        AIMessage(
            content="",
            tool_calls=[{"name": "search_products", "args": {"query": "jackets"}, "id": "1"}],
        ),
        ToolMessage(content="Ran search", tool_call_id="1"),
    ]

    assert should_extract_memories(messages) is True


async def test_extract_preference_facts_uses_llm_output():
    mock_response = SimpleNamespace(
        content='[{"category":"size","key":"hiking boots","value":"10"}]'
    )

    with patch(
        "app.services.memory_extractor.extractor_llm",
        new=SimpleNamespace(ainvoke=AsyncMock(return_value=mock_response)),
    ) as mock_ainvoke:
        memories = await extract_preference_facts(
            [HumanMessage(content="I wear a size 10 in hiking boots.")]
        )

    mock_ainvoke.ainvoke.assert_awaited_once()
    assert memories == [
        ExtractedMemory(category=MemoryCategory.SIZE, key="hiking boots", value="10"),
    ]


async def test_extract_and_store_memories_upserts_with_confidence(db):
    with patch(
        "app.services.memory_extractor.extract_preference_facts",
        new=AsyncMock(
            side_effect=[
                [ExtractedMemory(category=MemoryCategory.BRAND, key="jackets", value="Patagonia")],
                [ExtractedMemory(category=MemoryCategory.BRAND, key="jackets", value="Arc'teryx")],
            ]
        ),
    ):
        inserted = await extract_and_store_memories(
            db,
            "memory-user",
            [HumanMessage(content="I usually buy Patagonia jackets.")],
            source_message_id=123,
        )
        updated = await extract_and_store_memories(
            db,
            "memory-user",
            [HumanMessage(content="Actually I prefer Arc'teryx jackets.")],
            source_message_id=456,
        )

    assert inserted == 1
    assert updated == 1

    result = await db.execute(select(UserMemory).where(UserMemory.user_id == "memory-user"))
    memory = result.scalar_one()
    assert memory.value == "Arc'teryx"
    assert Decimal(str(memory.confidence)) == Decimal("0.6")
    assert memory.source_message_id == 456
