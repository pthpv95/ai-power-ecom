"""
Test fixtures shared across all test files.

Key decisions:
  - We use the SAME database as dev (aishop) but clean up after each test.
    In production you'd use a separate test database, but for learning this is simpler.
  - Each test gets its own DB session that rolls back after the test,
    so tests never leave dirty data behind.
  - We override FastAPI's get_db dependency to use the test session.
"""
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import Product, CartItem


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a test DB session that rolls back after each test.

    We create the engine INSIDE the fixture so it's always bound to
    the current event loop. A module-level engine would be created on
    import (one loop) but used in tests (different loop per function),
    causing "Future attached to a different loop" errors.
    """
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        yield session

        await session.close()
        await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP test client that uses the test DB session.

    We override get_db so all endpoint code uses our rolled-back session.
    """
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_products(db: AsyncSession) -> list[Product]:
    """Seed 3 test products into the database."""
    products = [
        Product(
            name="Test Rain Jacket",
            description="Waterproof jacket for rainy hikes",
            price=74.99,
            category="jackets",
            brand="TestBrand",
            stock=10,
        ),
        Product(
            name="Test Hiking Boots",
            description="Sturdy boots for mountain trails",
            price=89.99,
            category="footwear",
            brand="TestBrand",
            stock=5,
        ),
        Product(
            name="Test Sleeping Bag",
            description="Warm sleeping bag for cold nights",
            price=149.99,
            category="sleeping",
            brand="TestBrand",
            stock=0,  # out of stock — useful for testing filters
        ),
    ]
    db.add_all(products)
    await db.flush()  # assigns IDs without committing
    return products


@pytest_asyncio.fixture
async def sample_cart_item(db: AsyncSession, sample_products: list[Product]) -> CartItem:
    """Add the first test product to the cart."""
    item = CartItem(
        user_id="test_user",
        product_id=sample_products[0].id,
        quantity=2,
    )
    db.add(item)
    await db.flush()
    return item
