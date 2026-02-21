"""Tests for cart endpoints: GET /api/cart/:user_id, POST /api/cart, DELETE /api/cart/:item_id."""


async def test_get_empty_cart(client):
    """Empty cart returns zero items and zero total."""
    response = await client.get("/api/cart/test_user")
    assert response.status_code == 200

    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_add_to_cart(client, sample_products):
    """Adding a product creates a cart item with product details."""
    product = sample_products[0]
    response = await client.post("/api/cart", json={
        "user_id": "test_user",
        "product_id": product.id,
        "quantity": 2,
    })
    assert response.status_code == 201

    data = response.json()
    assert data["product_id"] == product.id
    assert data["quantity"] == 2
    assert data["product"]["name"] == "Test Rain Jacket"


async def test_add_to_cart_upsert(client, sample_products):
    """Adding the same product twice increases quantity (upsert)."""
    product = sample_products[0]
    payload = {"user_id": "test_user", "product_id": product.id, "quantity": 1}

    await client.post("/api/cart", json=payload)
    response = await client.post("/api/cart", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["quantity"] == 2  # 1 + 1


async def test_add_to_cart_product_not_found(client):
    """Adding a non-existent product returns 404."""
    response = await client.post("/api/cart", json={
        "user_id": "test_user",
        "product_id": 99999,
        "quantity": 1,
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


async def test_cart_total(client, sample_products):
    """Cart total sums price * quantity for all items."""
    # Add two different products
    await client.post("/api/cart", json={
        "user_id": "test_user",
        "product_id": sample_products[0].id,  # $74.99
        "quantity": 2,
    })
    await client.post("/api/cart", json={
        "user_id": "test_user",
        "product_id": sample_products[1].id,  # $89.99
        "quantity": 1,
    })

    response = await client.get("/api/cart/test_user")
    data = response.json()
    assert len(data["items"]) == 2
    # 74.99 * 2 + 89.99 * 1 = 239.97
    assert data["total"] == 239.97


async def test_remove_from_cart(client, sample_cart_item):
    """Deleting a cart item returns 204."""
    response = await client.delete(f"/api/cart/{sample_cart_item.id}")
    assert response.status_code == 204

    # Verify it's gone
    cart = await client.get("/api/cart/test_user")
    assert cart.json()["items"] == []


async def test_remove_from_cart_not_found(client):
    """Deleting a non-existent cart item returns 404."""
    response = await client.delete("/api/cart/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"


async def test_carts_are_per_user(client, sample_products):
    """Different user_ids have separate carts."""
    product = sample_products[0]
    await client.post("/api/cart", json={
        "user_id": "alice", "product_id": product.id, "quantity": 1,
    })
    await client.post("/api/cart", json={
        "user_id": "bob", "product_id": product.id, "quantity": 3,
    })

    alice_cart = await client.get("/api/cart/alice")
    bob_cart = await client.get("/api/cart/bob")

    assert len(alice_cart.json()["items"]) == 1
    assert alice_cart.json()["items"][0]["quantity"] == 1
    assert len(bob_cart.json()["items"]) == 1
    assert bob_cart.json()["items"][0]["quantity"] == 3
