"""Tests for chat message loading: GET /api/chat/:conversation_id/messages."""
from app.models import Message


async def test_load_messages_empty(client):
    """Unknown conversation returns an empty list."""
    response = await client.get("/api/chat/nonexistent-convo/messages?user_id=test_user")
    assert response.status_code == 200
    assert response.json() == []


async def test_load_messages(client, db):
    """Returns all messages for a conversation."""
    convo_id = "test-convo-123"
    db.add_all([
        Message(conversation_id=convo_id, role="user", content="Hi there", user_id="test_user"),
        Message(conversation_id=convo_id, role="assistant", content="Hello! How can I help?", user_id="test_user"),
        Message(conversation_id=convo_id, role="user", content="Show me jackets", user_id="test_user"),
    ])
    await db.flush()

    response = await client.get(f"/api/chat/{convo_id}/messages?user_id=test_user")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 3
    # All messages present (order may vary when timestamps are identical)
    contents = {m["content"] for m in data}
    assert "Hi there" in contents
    assert "Hello! How can I help?" in contents
    assert "Show me jackets" in contents


async def test_messages_scoped_to_conversation(client, db):
    """Messages from other conversations are not returned."""
    db.add_all([
        Message(conversation_id="convo-a", role="user", content="msg in A", user_id="test_user"),
        Message(conversation_id="convo-b", role="user", content="msg in B", user_id="test_user"),
    ])
    await db.flush()

    response = await client.get("/api/chat/convo-a/messages?user_id=test_user")
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "msg in A"
