"""
Agent tools — the actions GPT-4o can take.

Each tool is a plain function decorated with @tool.
LangGraph reads the function name, docstring, and type hints
to generate the JSON schema GPT-4o sees.

IMPORTANT: The docstring IS the tool description.
Write it like you're explaining to a smart assistant when to use this tool.
GPT-4o uses it to decide whether to call it.

db and user_id come from contextvars (set per-request in the chat endpoint),
NOT from function arguments. This keeps them invisible to GPT-4o's schema.
"""
from langchain_core.tools import tool

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.models import Product, CartItem
from app.services.search import semantic_search
from app.agent.context import db_var, user_id_var


def format_product(p: Product) -> str:
    """Format a product as a readable string for the LLM."""
    return (
        f"[ID:{p.id}] {p.name} — ${p.price:.2f}\n"
        f"  Brand: {p.brand} | Category: {p.category} | Stock: {p.stock}\n"
        f"  {p.description}"
    )


# ── Tool 1: search_products ──────────────────────────────────────────────────

@tool
async def search_products(
    query: str,
    max_price: float | None = None,
    category: str | None = None,
) -> str:
    """Search for products by natural language query.
    Use this when the user asks about products, gear recommendations,
    or anything shopping-related. Supports optional price and category filters.

    Available categories (use exact values): jackets, footwear, sleeping, packs, lighting, hydration, cooking, accessories, safety.
    Only pass category if the user explicitly mentions one. Let the semantic search handle discovery otherwise.
    """
    db = db_var.get()
    products = await semantic_search(
        query=query,
        db=db,
        max_price=max_price,
        category=category,
    )
    if not products:
        return "No products found matching your search."
    return "\n\n".join(format_product(p) for p in products)


# ── Tool 2: get_product_details ──────────────────────────────────────────────

@tool
async def get_product_details(product_id: int) -> str:
    """Get full details for a specific product by its ID.
    Use this when the user asks for more information about a specific product
    they've seen in search results.
    """
    db = db_var.get()
    product = await db.get(Product, product_id)
    if not product:
        return f"Product with ID {product_id} not found."
    return format_product(product)


# ── Tool 3: add_to_cart ──────────────────────────────────────────────────────

@tool
async def add_to_cart(product_id: int, quantity: int = 1) -> str:
    """Add a product to the user's shopping cart.
    Use this when the user says they want to buy, add, or get a product.
    If the user refers to a product from a previous comparison (e.g. "add the cheaper one",
    "add the most expensive one"), look up the [ID:X] tags and prices in your earlier messages
    to resolve the correct product_id — do NOT ask for clarification.
    """
    db = db_var.get()
    user_id = user_id_var.get()

    product = await db.get(Product, product_id)
    if not product:
        return f"Product with ID {product_id} not found."

    result = await db.execute(
        select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
    )
    cart_item = result.scalar_one_or_none()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        db.add(cart_item)

    await db.commit()
    return f"Added {quantity}x {product.name} (${product.price:.2f}) to your cart."


# ── Tool 4: remove_from_cart ─────────────────────────────────────────────────

@tool
async def remove_from_cart(product_id: int) -> str:
    """Remove a product from the user's cart.
    Use this when the user wants to remove or delete an item from their cart.
    """
    db = db_var.get()
    user_id = user_id_var.get()

    result = await db.execute(
        select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
    )
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        return "That product is not in your cart."

    await db.delete(cart_item)
    await db.commit()
    return f"Removed the item from your cart."


# ── Tool 5: clear_cart ───────────────────────────────────────────────────────

@tool
async def clear_cart() -> str:
    """Remove ALL items from the user's cart at once.
    Use this when the user wants to empty, clear, or reset their entire cart
    (e.g. "clear my cart", "remove everything", "start over").
    Do NOT use this to remove a single item — use remove_from_cart instead.
    """
    db = db_var.get()
    user_id = user_id_var.get()

    result = await db.execute(
        delete(CartItem).where(CartItem.user_id == user_id)
    )
    await db.commit()

    if result.rowcount == 0:
        return "Your cart is already empty."
    return f"Done! Removed all {result.rowcount} item(s) from your cart."


# ── Tool 6: get_current_cart ─────────────────────────────────────────────────

@tool
async def get_current_cart() -> str:
    """Get the current contents of the user's shopping cart.
    Use this when the user asks what's in their cart, the total, or wants to review.
    """
    db = db_var.get()
    user_id = user_id_var.get()

    result = await db.execute(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .options(selectinload(CartItem.product))
    )
    items = result.scalars().all()

    if not items:
        return "Your cart is empty."

    lines = []
    total = 0.0
    for item in items:
        subtotal = float(item.product.price) * item.quantity
        total += subtotal
        lines.append(f"• [ID:{item.product.id}] {item.product.name} x{item.quantity} — ${subtotal:.2f}")

    lines.append(f"\nTotal: ${total:.2f}")
    return "\n".join(lines)


# ── Tool 7: compare_products ─────────────────────────────────────────────────

@tool
async def compare_products(product_ids: list[int]) -> str:
    """Compare multiple products side by side.
    Use this when the user wants to compare two or more products.
    Takes a list of product IDs.
    """
    db = db_var.get()

    result = await db.execute(
        select(Product).where(Product.id.in_(product_ids))
    )
    products = result.scalars().all()

    if len(products) < 2:
        return "Need at least 2 valid product IDs to compare."

    lines = []
    for p in products:
        lines.append(format_product(p))
    return "\n\n--- vs ---\n\n".join(lines)


ALL_TOOLS = [
    search_products,
    get_product_details,
    add_to_cart,
    remove_from_cart,
    clear_cart,
    get_current_cart,
    compare_products,
]
