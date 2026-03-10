from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langchain_core.messages import HumanMessage

from app.agent.context import db_var, user_id_var
from app.agent.graph import build_system_prompt_with_memories
from app.services.conversation import save_message
from app.services.memory_extractor import extract_and_store_memories


async def test_memory_extraction_then_prompt_injection(db):
    user_id = "integration-memory-user"
    conversation_id = "memory-flow"
    user_message = await save_message(
        db,
        conversation_id,
        "user",
        "I usually buy Patagonia jackets and keep boots under $150.",
        user_id=user_id,
    )

    with patch(
        "app.services.memory_extractor.extractor_llm",
        new=SimpleNamespace(
            ainvoke=AsyncMock(
                return_value=SimpleNamespace(
                    content=(
                        '[{"category":"brand","key":"jackets","value":"Patagonia"},'
                        '{"category":"budget","key":"boots","value":"under $150"}]'
                    )
                )
            )
        ),
    ):
        stored = await extract_and_store_memories(
            db,
            user_id,
            [HumanMessage(content=user_message.content)],
            source_message_id=user_message.id,
        )

    assert stored == 2

    db_var.set(db)
    user_id_var.set(user_id)
    prompt = await build_system_prompt_with_memories()

    assert "Known user preferences" in prompt
    assert "jackets: Patagonia" in prompt
    assert "boots: under $150" in prompt
