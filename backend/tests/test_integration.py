"""
Integration tests — full workflows that cross multiple layers.

These chain together tools, services, and endpoints to simulate
real user scenarios end-to-end (minus the LLM decision-making).

Think of these like Playwright tests but for the backend: they test
the full path a request takes through the system.
"""
from app.agent.context import db_var, user_id_var
from app.agent.tools import (
    add_to_cart,
    get_current_cart,
    get_product_details,
    remove_from_cart,
    search_products,
)
from app.models import Message
from app.services.conversation import save_message, load_messages


def setup_context(db, user_id="test_user"):
    db_var.set(db)
    user_id_var.set(user_id)


# ── Full shopping workflow ───────────────────────────────────────────────────

async def test_browse_and_buy_flow(db, sample_products):
    """
    Simulates a real user session (without the LLM choosing tools):
      1. Get details on a product
      2. Add it to cart
      3. Add a second product
      4. Check the cart (both items, correct total)
      5. Remove one item
      6. Check cart again (only one item left)
    """
    setup_context(db)
    jacket = sample_products[0]   # $74.99
    boots = sample_products[1]    # $89.99

    # Step 1: get details
    details = await get_product_details.ainvoke({"product_id": jacket.id})
    assert "Test Rain Jacket" in details
    assert "$74.99" in details

    # Step 2: add jacket to cart
    result = await add_to_cart.ainvoke({"product_id": jacket.id, "quantity": 1})
    assert "Added" in result

    # Step 3: add boots to cart
    result = await add_to_cart.ainvoke({"product_id": boots.id, "quantity": 2})
    assert "Added 2x Test Hiking Boots" in result

    # Step 4: check full cart
    cart = await get_current_cart.ainvoke({})
    assert "Test Rain Jacket" in cart
    assert "Test Hiking Boots" in cart
    # 74.99 * 1 + 89.99 * 2 = 254.97
    assert "$254.97" in cart

    # Step 5: remove jacket
    result = await remove_from_cart.ainvoke({"product_id": jacket.id})
    assert "Removed" in result

    # Step 6: only boots remain
    cart = await get_current_cart.ainvoke({})
    assert "Test Rain Jacket" not in cart
    assert "Test Hiking Boots" in cart
    assert "$179.98" in cart  # 89.99 * 2


async def test_multi_user_isolation(db, sample_products):
    """Two users shopping simultaneously don't see each other's carts."""
    product = sample_products[0]

    # Alice adds 1
    setup_context(db, user_id="alice")
    await add_to_cart.ainvoke({"product_id": product.id, "quantity": 1})

    # Bob adds 3
    setup_context(db, user_id="bob")
    await add_to_cart.ainvoke({"product_id": product.id, "quantity": 3})

    # Alice's cart: 1x
    setup_context(db, user_id="alice")
    alice_cart = await get_current_cart.ainvoke({})
    assert "x1" in alice_cart

    # Bob's cart: 3x
    setup_context(db, user_id="bob")
    bob_cart = await get_current_cart.ainvoke({})
    assert "x3" in bob_cart


# ── Conversation persistence ─────────────────────────────────────────────────

async def test_save_and_load_messages(db):
    """Messages are persisted and loaded in chronological order."""
    convo_id = "integration-test-convo"

    await save_message(db, convo_id, "user", "Show me rain jackets")
    await save_message(db, convo_id, "assistant", "Here are some jackets...")
    await save_message(db, convo_id, "user", "Add the first one to my cart")

    messages = await load_messages(db, convo_id)
    assert len(messages) == 3
    assert messages[0].role == "user"
    assert messages[0].content == "Show me rain jackets"
    assert messages[1].role == "assistant"
    assert messages[2].content == "Add the first one to my cart"


async def test_conversations_are_isolated(db):
    """Messages from different conversations don't leak."""
    await save_message(db, "convo-A", "user", "msg in A")
    await save_message(db, "convo-B", "user", "msg in B")

    a_msgs = await load_messages(db, "convo-A")
    b_msgs = await load_messages(db, "convo-B")

    assert len(a_msgs) == 1
    assert a_msgs[0].content == "msg in A"
    assert len(b_msgs) == 1
    assert b_msgs[0].content == "msg in B"


async def test_load_via_endpoint_after_save(client, db):
    """
    Save messages via the service, then load them via the HTTP endpoint.
    This crosses the service → endpoint boundary.
    """
    convo_id = "endpoint-load-test"
    await save_message(db, convo_id, "user", "Hello")
    await save_message(db, convo_id, "assistant", "Hi there!")

    response = await client.get(f"/api/chat/{convo_id}/messages")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "Hello"
    assert data[1]["role"] == "assistant"
    assert data[1]["content"] == "Hi there!"
    # Verify each message has an ID and timestamp
    assert data[0]["id"] is not None
    assert data[0]["created_at"] is not None
