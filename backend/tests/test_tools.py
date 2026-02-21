"""
Tests for agent tools — call each tool directly with contextvars.

These tests verify the tool LOGIC works correctly, without involving
the LLM at all. Think of it like testing Express middleware/handlers
without going through the HTTP layer.

Key pattern: set db_var and user_id_var before calling the tool,
just like the chat endpoint does per-request.
"""
from app.agent.context import db_var, user_id_var
from app.agent.tools import (
    add_to_cart,
    compare_products,
    get_current_cart,
    get_product_details,
    remove_from_cart,
    search_products,
)
from app.models import CartItem, Product


# ── Helpers ──────────────────────────────────────────────────────────────────

def setup_context(db, user_id="test_user"):
    """Set contextvars for tool calls — equivalent to what the chat endpoint does."""
    db_var.set(db)
    user_id_var.set(user_id)


# ── get_product_details ──────────────────────────────────────────────────────

async def test_get_product_details(db, sample_products):
    setup_context(db)
    result = await get_product_details.ainvoke({"product_id": sample_products[0].id})
    assert "Test Rain Jacket" in result
    assert "$74.99" in result


async def test_get_product_details_not_found(db):
    setup_context(db)
    result = await get_product_details.ainvoke({"product_id": 99999})
    assert "not found" in result


# ── add_to_cart ──────────────────────────────────────────────────────────────

async def test_add_to_cart(db, sample_products):
    setup_context(db)
    result = await add_to_cart.ainvoke({
        "product_id": sample_products[0].id,
        "quantity": 2,
    })
    assert "Added 2x Test Rain Jacket" in result
    assert "$74.99" in result


async def test_add_to_cart_upsert(db, sample_products):
    """Adding same product twice increases quantity."""
    setup_context(db)
    product_id = sample_products[0].id

    await add_to_cart.ainvoke({"product_id": product_id, "quantity": 1})
    await add_to_cart.ainvoke({"product_id": product_id, "quantity": 3})

    # Verify quantity is 4 (1 + 3)
    cart_result = await get_current_cart.ainvoke({})
    assert "x4" in cart_result


async def test_add_to_cart_not_found(db):
    setup_context(db)
    result = await add_to_cart.ainvoke({"product_id": 99999})
    assert "not found" in result


# ── get_current_cart ─────────────────────────────────────────────────────────

async def test_get_cart_empty(db):
    setup_context(db)
    result = await get_current_cart.ainvoke({})
    assert "empty" in result.lower()


async def test_get_cart_with_items(db, sample_products):
    setup_context(db)
    await add_to_cart.ainvoke({"product_id": sample_products[0].id, "quantity": 2})
    await add_to_cart.ainvoke({"product_id": sample_products[1].id, "quantity": 1})

    result = await get_current_cart.ainvoke({})
    assert "Test Rain Jacket" in result
    assert "Test Hiking Boots" in result
    assert "Total:" in result
    # 74.99 * 2 + 89.99 * 1 = 239.97
    assert "$239.97" in result


# ── remove_from_cart ─────────────────────────────────────────────────────────

async def test_remove_from_cart(db, sample_products):
    setup_context(db)
    product_id = sample_products[0].id

    # Add then remove
    await add_to_cart.ainvoke({"product_id": product_id})
    result = await remove_from_cart.ainvoke({"product_id": product_id})
    assert "Removed" in result

    # Cart should be empty now
    cart = await get_current_cart.ainvoke({})
    assert "empty" in cart.lower()


async def test_remove_from_cart_not_in_cart(db):
    setup_context(db)
    result = await remove_from_cart.ainvoke({"product_id": 99999})
    assert "not in your cart" in result


# ── compare_products ─────────────────────────────────────────────────────────

async def test_compare_products(db, sample_products):
    setup_context(db)
    ids = [sample_products[0].id, sample_products[1].id]
    result = await compare_products.ainvoke({"product_ids": ids})
    assert "Test Rain Jacket" in result
    assert "Test Hiking Boots" in result
    assert "vs" in result


async def test_compare_products_need_two(db, sample_products):
    setup_context(db)
    result = await compare_products.ainvoke({"product_ids": [sample_products[0].id]})
    assert "at least 2" in result
