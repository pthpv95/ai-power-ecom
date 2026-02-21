"""Tests for product endpoints: GET /api/products, GET /api/products/:id, POST /api/products."""


async def test_list_products(client):
    """Returns products from the database."""
    response = await client.get("/api/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_list_products_includes_fixtures(client, sample_products):
    """Fixture products appear in the list alongside seeded data."""
    response = await client.get("/api/products")
    assert response.status_code == 200

    data = response.json()
    names = {p["name"] for p in data}
    assert "Test Rain Jacket" in names
    assert "Test Hiking Boots" in names


async def test_get_product_by_id(client, sample_products):
    """Fetching a single product returns correct data."""
    product_id = sample_products[0].id
    response = await client.get(f"/api/products/{product_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Test Rain Jacket"
    assert data["price"] == 74.99
    assert data["category"] == "jackets"


async def test_get_product_not_found(client):
    """Non-existent product returns 404."""
    response = await client.get("/api/products/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


async def test_create_product(client):
    """POST creates a product and returns it with an ID."""
    payload = {
        "name": "Trail Socks",
        "description": "Moisture-wicking hiking socks",
        "price": 19.99,
        "category": "accessories",
        "brand": "SockCo",
        "stock": 50,
    }
    response = await client.post("/api/products", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Trail Socks"
    assert data["stock"] == 50


async def test_create_product_missing_fields(client):
    """POST with missing required fields returns 422 validation error."""
    response = await client.post("/api/products", json={"name": "Incomplete"})
    assert response.status_code == 422
