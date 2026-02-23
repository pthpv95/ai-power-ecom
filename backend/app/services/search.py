from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.services.embeddings import embed_text
from app.services.vector_store import search_similar


async def semantic_search(
    query: str,
    db: AsyncSession,
    max_price: float | None = None,
    category: str | None = None,
    in_stock_only: bool = True,
    top_k: int = 10,
) -> list[Product]:
    """
    Full RAG pipeline:
      1. Embed the query                     (OpenAI)
      2. Find semantically similar products  (Pinecone)
      3. Fetch full records + apply filters  (PostgreSQL)

    Why this split?
    - Pinecone handles "find me things about warm camping gear"
    - PostgreSQL handles "but only under $100 and in stock"
    Embeddings can't reliably encode numeric constraints,
    so we let SQL do what SQL is good at.
    """

    # Step 1: Embed the query
    query_vector = await embed_text(query)

    # Step 2: Get top-k similar product IDs from Pinecone
    # We fetch more than needed because SQL filters may reduce the count
    matches = search_similar(query_vector, top_k=top_k * 2)

    if not matches:
        return []

    # Extract product IDs in similarity order (best match first)
    product_ids = [int(m.id) for m in matches]

    # Step 3: Fetch full records from PostgreSQL
    stmt = select(Product).where(Product.id.in_(product_ids))

    # Apply hard filters — things embeddings can't handle reliably
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    if category is not None:
        stmt = stmt.where(Product.category.ilike(f"%{category}%"))
    if in_stock_only:
        stmt = stmt.where(Product.stock > 0)

    result = await db.execute(stmt)
    products_by_id = {p.id: p for p in result.scalars().all()}

    # Step 4: Re-sort by Pinecone similarity score
    # SQL's IN clause doesn't preserve order, so we restore it manually
    sorted_products = [
        products_by_id[pid]
        for pid in product_ids
        if pid in products_by_id
    ]

    return sorted_products[:top_k]
