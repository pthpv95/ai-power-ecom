"""Smoke test — verify test infrastructure works."""


async def test_db_session_works(db):
    """Test that we can query the database."""
    from sqlalchemy import text
    result = await db.execute(text("SELECT 1"))
    assert result.scalar() == 1


async def test_client_works(client):
    """Test that the HTTP client can hit endpoints."""
    response = await client.get("/api/health")
    assert response.status_code == 200


async def test_fixtures_work(sample_products):
    """Test that fixture creates products with IDs."""
    assert len(sample_products) == 3
    assert all(p.id is not None for p in sample_products)
