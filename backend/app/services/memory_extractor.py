import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import MemoryCategory, Message, UserMemory

logger = logging.getLogger(__name__)

EXTRACTION_MODEL = "gpt-4o-mini"
DEFAULT_MEMORY_CONFIDENCE = Decimal("0.5")
CONFIDENCE_STEP = Decimal("0.1")
MAX_MEMORY_CONFIDENCE = Decimal("1.0")
PRODUCT_KEYWORDS = {
    "boot",
    "boots",
    "jacket",
    "jackets",
    "shoe",
    "shoes",
    "tent",
    "sleeping bag",
    "backpack",
    "pack",
    "gear",
    "outdoor",
    "hiking",
    "trail",
    "waterproof",
    "brand",
    "size",
    "budget",
    "price",
    "cart",
    "product",
}

extractor_llm = ChatOpenAI(
    model=EXTRACTION_MODEL,
    api_key=settings.openai_api_key,
    temperature=0,
)


@dataclass(slots=True)
class ExtractedMemory:
    category: MemoryCategory
    key: str
    value: str


def should_extract_memories(messages: Sequence[Message | BaseMessage | dict[str, Any] | str]) -> bool:
    for message in messages:
        if _message_has_tool_signal(message):
            return True
        content = _message_content(message).lower()
        if any(keyword in content for keyword in PRODUCT_KEYWORDS):
            return True
    return False


async def extract_preference_facts(
    messages: Sequence[Message | BaseMessage | dict[str, Any] | str],
) -> list[ExtractedMemory]:
    if not should_extract_memories(messages):
        return []

    conversation_text = _messages_to_text(messages)
    response = await extractor_llm.ainvoke(
        [
            HumanMessage(
                content=(
                    "Extract durable shopping preference facts from this conversation. "
                    "Return JSON only as an array of objects with keys: category, key, value. "
                    "Allowed categories: brand, size, budget, category, style, other. "
                    "Only include stable user preferences or constraints. "
                    "If there are none, return [].\n\n"
                    f"{conversation_text}"
                )
            )
        ]
    )
    return parse_extracted_memories(response.content)


async def upsert_memories(
    db: AsyncSession,
    user_id: str,
    memories: Sequence[ExtractedMemory],
    *,
    source_message_id: int | None = None,
) -> int:
    if not memories:
        return 0

    inserted_or_updated = 0
    for memory in memories:
        result = await db.execute(
            select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.category == memory.category,
                UserMemory.key == memory.key,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            db.add(
                UserMemory(
                    user_id=user_id,
                    category=memory.category,
                    key=memory.key,
                    value=memory.value,
                    confidence=DEFAULT_MEMORY_CONFIDENCE,
                    source_message_id=source_message_id,
                )
            )
        else:
            existing.value = memory.value
            existing.source_message_id = source_message_id
            existing.confidence = min(
                MAX_MEMORY_CONFIDENCE,
                Decimal(str(existing.confidence)) + CONFIDENCE_STEP,
            )
        inserted_or_updated += 1

    await db.commit()
    return inserted_or_updated


async def extract_and_store_memories(
    db: AsyncSession,
    user_id: str,
    messages: Sequence[Message | BaseMessage | dict[str, Any] | str],
    *,
    source_message_id: int | None = None,
) -> int:
    memories = await extract_preference_facts(messages)
    return await upsert_memories(
        db,
        user_id,
        memories,
        source_message_id=source_message_id,
    )


def parse_extracted_memories(payload: str) -> list[ExtractedMemory]:
    raw_items = _parse_json_payload(payload)
    memories: list[ExtractedMemory] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        value = str(item.get("value", "")).strip()
        if not key or not value:
            continue
        memories.append(
            ExtractedMemory(
                category=normalize_memory_category(item.get("category")),
                key=key,
                value=value,
            )
        )
    return memories


def normalize_memory_category(category: Any) -> MemoryCategory:
    if isinstance(category, MemoryCategory):
        return category

    raw = str(category or "").strip().lower()
    aliases = {
        "brand_preference": MemoryCategory.BRAND,
        "brands": MemoryCategory.BRAND,
        "sizes": MemoryCategory.SIZE,
        "budget_range": MemoryCategory.BUDGET,
        "price": MemoryCategory.BUDGET,
        "product_category": MemoryCategory.CATEGORY,
        "interest": MemoryCategory.CATEGORY,
        "aesthetic": MemoryCategory.STYLE,
    }
    normalized = aliases.get(raw, raw)
    try:
        return MemoryCategory(normalized)
    except ValueError:
        return MemoryCategory.OTHER


def _messages_to_text(messages: Sequence[Message | BaseMessage | dict[str, Any] | str]) -> str:
    return "\n".join(
        f"{_message_role(message)}: {_message_content(message)}"
        for message in messages
        if _message_content(message).strip()
    )


def _message_role(message: Message | BaseMessage | dict[str, Any] | str) -> str:
    if isinstance(message, Message):
        return message.role.capitalize()
    if isinstance(message, ToolMessage):
        return "Tool"
    if isinstance(message, HumanMessage):
        return "User"
    if isinstance(message, AIMessage):
        return "Assistant"
    if isinstance(message, dict):
        return str(message.get("role", "Message")).capitalize()
    return "Message"


def _message_content(message: Message | BaseMessage | dict[str, Any] | str) -> str:
    if isinstance(message, Message):
        return message.content
    if isinstance(message, BaseMessage):
        content = message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                str(part.get("text", "")) if isinstance(part, dict) else str(part)
                for part in content
            )
        return str(content)
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(message)


def _message_has_tool_signal(message: Message | BaseMessage | dict[str, Any] | str) -> bool:
    if isinstance(message, ToolMessage):
        return True
    if isinstance(message, AIMessage):
        return bool(message.tool_calls)
    if isinstance(message, dict):
        return bool(message.get("tool_calls")) or message.get("role") == "tool"
    return False


def _parse_json_payload(payload: str) -> list[Any]:
    cleaned = payload.strip()
    if cleaned.startswith("```"):
        lines = [line.strip() for line in cleaned.splitlines()]
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Memory extraction returned invalid JSON", extra={"payload": payload})
        return []

    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        memories = parsed.get("memories")
        if isinstance(memories, list):
            return memories
    return []
