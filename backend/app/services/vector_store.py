from pinecone import Pinecone
from app.config import settings

# Pinecone client is synchronous — we initialize it once at module level
# (same singleton pattern as the SQLAlchemy engine)
pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index(settings.pinecone_index)


def upsert_products(vectors: list[tuple[str, list[float], dict]]) -> None:
    """
    Store product vectors in Pinecone.

    Each item in `vectors` is a tuple of:
      - id:       string ID (we use str(product.id))
      - values:   the embedding vector (1536 floats)
      - metadata: dict of extra fields stored alongside the vector
                  (we store product_id so we can fetch from PostgreSQL later)

    Why store metadata?
    Pinecone only returns IDs and scores. We store product_id in metadata
    as a convenience — they're the same here, but in larger systems
    the Pinecone ID and the DB primary key might differ.
    """
    records = [
        {"id": id_, "values": values, "metadata": metadata}
        for id_, values, metadata in vectors
    ]
    index.upsert(vectors=records)


def search_similar(query_vector: list[float], top_k: int = 10) -> list[dict]:
    """
    Find the top-k most similar products to the query vector.

    Returns a list of matches, each with:
      - id:       the Pinecone record ID
      - score:    cosine similarity (0.0 to 1.0, higher = more similar)
      - metadata: whatever we stored during upsert

    We fetch more than we need (top_k=10) because some will be
    filtered out by SQL constraints (price, stock) in the next step.
    """
    result = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
    )
    return result.matches
