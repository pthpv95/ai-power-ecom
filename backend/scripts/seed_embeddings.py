"""
One-time script: embed all products and store them in Pinecone.

Run after seeding the database:
    uv run python scripts/seed_embeddings.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import SessionLocal
from app.models import Product
from app.services.embeddings import build_product_text, embed_texts
from app.services.vector_store import upsert_products


async def main():
    async with SessionLocal() as db:
        result = await db.execute(select(Product))
        products = result.scalars().all()

    if not products:
        print("No products found. Run seed.py first.")
        return

    print(f"Embedding {len(products)} products...")

    # Build the text for each product
    texts = [build_product_text(p) for p in products]

    # One batched API call for all products (efficient)
    vectors = await embed_texts(texts)

    # Prepare records for Pinecone: (id, vector, metadata)
    records = [
        (
            str(p.id),                        # Pinecone ID must be a string
            vectors[i],                        # 1536-dim embedding
            {"product_id": p.id, "name": p.name, "category": p.category},
        )
        for i, p in enumerate(products)
    ]

    upsert_products(records)
    print(f"Done! {len(records)} products stored in Pinecone.")

    # Show a sample so you can see what was embedded
    print("\nSample embedded text:")
    print(f"  [{products[0].name}]")
    print(f"  → '{texts[0]}'")


if __name__ == "__main__":
    asyncio.run(main())
