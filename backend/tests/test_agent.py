"""
Tests for agent graph logic and guardrails.

These test the "wiring" — does the graph route correctly?
Does the guardrail reject oversized messages?
No LLM calls needed for most of these.
"""
import json

from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph import should_continue


# ── should_continue (routing logic) ─────────────────────────────────────────

def test_should_continue_routes_to_tools():
    """When the LLM returns tool_calls, route to the tools node."""
    ai_msg = AIMessage(
        content="",
        tool_calls=[{"name": "search_products", "args": {"query": "rain"}, "id": "1"}],
    )
    state = {"messages": [HumanMessage(content="hi"), ai_msg]}
    assert should_continue(state) == "tools"


def test_should_continue_routes_to_end():
    """When the LLM returns a plain text response, route to end."""
    ai_msg = AIMessage(content="Here are some jackets for you!")
    state = {"messages": [HumanMessage(content="hi"), ai_msg]}
    assert should_continue(state) == "end"


def test_should_continue_empty_tool_calls():
    """AIMessage with empty tool_calls list routes to end."""
    ai_msg = AIMessage(content="No tools needed.", tool_calls=[])
    state = {"messages": [ai_msg]}
    assert should_continue(state) == "end"


# ── Guardrails (via streaming endpoint) ──────────────────────────────────────

async def test_message_too_long_rejected(client):
    """Messages over MAX_MESSAGE_LENGTH get a friendly rejection via SSE."""
    long_message = "x" * 2001  # MAX_MESSAGE_LENGTH is 2000
    response = await client.post("/api/chat/stream", json={
        "user_id": "test_user",
        "message": long_message,
    })
    assert response.status_code == 200  # SSE always returns 200

    # Parse SSE events from the response body
    events = _parse_sse(response.text)

    # Should contain a rejection message and a done event
    token_events = [e for e in events if e.get("type") == "token"]
    done_events = [e for e in events if e.get("type") == "done"]

    assert len(token_events) >= 1
    assert "too long" in token_events[0]["content"].lower()
    assert len(done_events) == 1


async def test_message_at_limit_accepted(client):
    """A message exactly at MAX_MESSAGE_LENGTH should NOT be rejected."""
    exact_message = "x" * 2000
    response = await client.post("/api/chat/stream", json={
        "user_id": "test_user",
        "message": exact_message,
    })
    assert response.status_code == 200

    events = _parse_sse(response.text)
    token_events = [e for e in events if e.get("type") == "token"]

    # Should NOT contain the rejection message
    if token_events:
        assert "too long" not in token_events[0].get("content", "").lower()


# ── SSE format helper ────────────────────────────────────────────────────────

def test_sse_event_format():
    """sse_event produces valid SSE format."""
    from app.api.chat import sse_event

    result = sse_event({"type": "token", "content": "hello"})
    assert result.startswith("data: ")
    assert result.endswith("\n\n")

    parsed = json.loads(result.removeprefix("data: ").strip())
    assert parsed["type"] == "token"
    assert parsed["content"] == "hello"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_sse(text: str) -> list[dict]:
    """Parse SSE response body into a list of event dicts."""
    events = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events
