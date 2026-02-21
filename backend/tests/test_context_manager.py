"""
Tests for context window management — token counting, message conversion,
and the sliding window + summarization logic.

build_context over-budget calls the real LLM (gpt-4o-mini) for summarization,
so we mock it to keep tests fast and free.
"""
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.models import Message
from app.services.context_manager import (
    MAX_HISTORY_TOKENS,
    MIN_RECENT_MESSAGES,
    build_context,
    count_tokens,
    messages_to_langchain,
)


# ── count_tokens ─────────────────────────────────────────────────────────────

def test_count_tokens_empty():
    assert count_tokens("") == 0


def test_count_tokens_simple():
    tokens = count_tokens("hello world")
    assert tokens == 2  # "hello" and "world" are each 1 token


def test_count_tokens_longer():
    """Longer text produces more tokens."""
    short = count_tokens("hi")
    long = count_tokens("This is a much longer sentence with many words in it")
    assert long > short


# ── messages_to_langchain ────────────────────────────────────────────────────

def test_messages_to_langchain_converts_roles():
    db_messages = [
        _make_message("user", "hello"),
        _make_message("assistant", "hi there"),
        _make_message("user", "show me jackets"),
    ]
    result = messages_to_langchain(db_messages)

    assert len(result) == 3
    assert isinstance(result[0], HumanMessage)
    assert isinstance(result[1], AIMessage)
    assert isinstance(result[2], HumanMessage)
    assert result[0].content == "hello"
    assert result[1].content == "hi there"


def test_messages_to_langchain_empty():
    assert messages_to_langchain([]) == []


# ── build_context ────────────────────────────────────────────────────────────

async def test_build_context_empty():
    """Empty message list returns empty context."""
    result = await build_context([])
    assert result == []


async def test_build_context_under_budget():
    """Short conversations are returned verbatim — no summarization."""
    db_messages = [
        _make_message("user", "Show me rain jackets"),
        _make_message("assistant", "Here are some options..."),
        _make_message("user", "What about the first one?"),
    ]
    result = await build_context(db_messages)

    assert len(result) == 3
    assert isinstance(result[0], HumanMessage)
    assert result[0].content == "Show me rain jackets"


async def test_build_context_over_budget_triggers_summarization():
    """
    When total tokens exceed MAX_HISTORY_TOKENS, older messages get
    summarized and only MIN_RECENT_MESSAGES are kept verbatim.
    """
    # Create enough messages to exceed the token budget.
    # Each message ~100 tokens, we need > MAX_HISTORY_TOKENS total.
    filler = "This is a detailed message about outdoor gear products. " * 20  # ~200 tokens each
    num_messages = 30  # 30 * ~200 = ~6000 tokens, well over 4000 budget

    db_messages = []
    for i in range(num_messages):
        role = "user" if i % 2 == 0 else "assistant"
        db_messages.append(_make_message(role, f"Message {i}: {filler}"))

    # Mock the summarizer so we don't call OpenAI
    mock_summary = "User browsed rain jackets and hiking boots. Added a jacket to cart."
    with patch(
        "app.services.context_manager.summarize_messages",
        new_callable=AsyncMock,
        return_value=mock_summary,
    ) as mock_summarize:
        result = await build_context(db_messages)

        # summarize_messages should have been called once
        mock_summarize.assert_called_once()

        # Result should be: [summary SystemMessage] + MIN_RECENT_MESSAGES
        assert len(result) == MIN_RECENT_MESSAGES + 1

        # First message is the summary
        assert isinstance(result[0], SystemMessage)
        assert "Summary of earlier conversation" in result[0].content
        assert mock_summary in result[0].content

        # Last messages are the recent ones, kept verbatim
        assert f"Message {num_messages - 1}" in result[-1].content


async def test_build_context_few_messages_no_summarization():
    """
    Even if messages are long, if there are <= MIN_RECENT_MESSAGES,
    no summarization happens (nothing old to summarize).
    """
    long_text = "word " * 2000  # ~2000 tokens, exceeds budget alone
    db_messages = [
        _make_message("user", long_text),
        _make_message("assistant", long_text),
    ]

    # Should NOT call summarizer — not enough messages to split
    with patch(
        "app.services.context_manager.summarize_messages",
        new_callable=AsyncMock,
    ) as mock_summarize:
        result = await build_context(db_messages)
        mock_summarize.assert_not_called()

    # Returns the recent messages (all of them, since len < MIN_RECENT_MESSAGES)
    assert len(result) == 2


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_message(role: str, content: str) -> Message:
    """Create a Message object without hitting the database."""
    return Message(role=role, content=content, conversation_id="test")
