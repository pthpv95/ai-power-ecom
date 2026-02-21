"""Tests for chat message loading: GET /api/chat/:conversation_id/messages."""
from app.models import Message


async def test_load_messages_empty(client):
    """Unknown conversation returns an empty list."""
    response = await client.get("/api/chat/nonexistent-convo/messages")
    assert response.status_code == 200
    assert response.json() == []


async def test_load_messages(client, db):
    """Returns messages in order for a conversation."""
    convo_id = "test-convo-123"
    db.add_all([
        Message(conversation_id=convo_id, role="user", content="Hi there"),
        Message(conversation_id=convo_id, role="assistant", content="Hello! How can I help?"),
        Message(conversation_id=convo_id, role="user", content="Show me jackets"),
    ])
    await db.flush()

    response = await client.get(f"/api/chat/{convo_id}/messages")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 3
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "Hi there"
    assert data[1]["role"] == "assistant"
    assert data[2]["content"] == "Show me jackets"


async def test_messages_scoped_to_conversation(client, db):
    """Messages from other conversations are not returned."""
    db.add_all([
        Message(conversation_id="convo-a", role="user", content="msg in A"),
        Message(conversation_id="convo-b", role="user", content="msg in B"),
    ])
    await db.flush()

    response = await client.get("/api/chat/convo-a/messages")
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "msg in A"
