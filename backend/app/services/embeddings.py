from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def build_product_text(product) -> str:
    """
    Construct the text we embed for each product.

    Why this matters: the quality of your search is directly tied to
    what text you embed. We want to pack in all the semantically
    meaningful fields — name, description, category, brand.
    We deliberately exclude price and stock because embeddings
    can't reliably encode numeric constraints (that's SQL's job).
    """
    return f"{product.name}. {product.description}. Category: {product.category}. Brand: {product.brand}."


async def embed_text(text: str) -> list[float]:
    """Embed a single string and return the vector."""
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple strings in one API call (batching).

    OpenAI allows up to 2048 inputs per request.
    Batching is more efficient than calling embed_text() in a loop —
    fewer HTTP round trips, lower latency, same cost per token.
    """
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    # Response comes back in the same order as input
    return [item.embedding for item in response.data]
