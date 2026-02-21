"""
Quick debug script to test each search layer independently.

Usage:
    uv run python scripts/test_search.py "rain gear"
    uv run python scripts/test_search.py "warm sleeping bag" --max-price 100
    uv run python scripts/test_search.py "lightweight" --category packs
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.services.embeddings import embed_text
from app.services.vector_store import search_similar
from app.services.search import semantic_search
from app.agent.context import db_var, user_id_var
from app.agent.tools import search_products


def parse_args():
    args = sys.argv[1:]
    if not args:
        print("Usage: uv run python scripts/test_search.py \"your query\" [--max-price 100] [--category packs]")
        sys.exit(1)

    query = args[0]
    max_price = None
    category = None

    for i, arg in enumerate(args[1:], 1):
        if arg == "--max-price" and i + 1 < len(args):
            max_price = float(args[i + 1])
        if arg == "--category" and i + 1 < len(args):
            category = args[i + 1]

    return query, max_price, category


async def main():
    query, max_price, category = parse_args()

    print(f'\nQuery: "{query}"')
    if max_price:
        print(f"Max price: ${max_price}")
    if category:
        print(f"Category: {category}")

    # Layer 1: Pinecone
    print("\n── Layer 1: Pinecone (vector search) ──")
    vec = await embed_text(query)
    matches = search_similar(vec, top_k=5)
    if not matches:
        print("  ❌ No matches from Pinecone")
        return
    for m in matches:
        print(f"  ✅ ID:{m.id}  score:{m.score:.4f}  {m.metadata.get('name', '?')}")

    # Layer 2: Full search (Pinecone + PostgreSQL)
    print("\n── Layer 2: Full search (Pinecone + PostgreSQL) ──")
    async with SessionLocal() as db:
        products = await semantic_search(
            query=query, db=db, max_price=max_price, category=category,
        )
        if not products:
            print("  ❌ No products after SQL filtering")
        else:
            for p in products:
                print(f"  ✅ ID:{p.id} {p.name} — ${p.price} (stock:{p.stock})")

    # Layer 3: Tool (what the agent sees)
    print("\n── Layer 3: Agent tool output ──")
    async with SessionLocal() as db:
        db_var.set(db)
        user_id_var.set("test_user")
        tool_args = {"query": query}
        if max_price:
            tool_args["max_price"] = max_price
        if category:
            tool_args["category"] = category
        result = await search_products.ainvoke(tool_args)
        print(result)

    print("\n✅ All layers passed")


if __name__ == "__main__":
    asyncio.run(main())
