from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import CartItem, Product
from app.schemas import CartItemAdd, CartItemResponse, CartResponse

router = APIRouter()


@router.get("/{user_id}", response_model=CartResponse)
async def get_cart(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .options(selectinload(CartItem.product))
    )
    items = result.scalars().all()
    total = sum(item.product.price * item.quantity for item in items)
    return CartResponse(items=items, total=round(total, 2))


@router.post("", response_model=CartItemResponse, status_code=201)
async def add_to_cart(body: CartItemAdd, db: AsyncSession = Depends(get_db)):
    # Check product exists
    product = await db.get(Product, body.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Upsert: update quantity if already in cart
    result = await db.execute(
        select(CartItem).where(
            CartItem.user_id == body.user_id,
            CartItem.product_id == body.product_id,
        )
    )
    cart_item = result.scalar_one_or_none()

    if cart_item:
        cart_item.quantity += body.quantity
    else:
        cart_item = CartItem(**body.model_dump())
        db.add(cart_item)

    await db.commit()
    await db.refresh(cart_item)

    # Reload with product relationship for response
    result = await db.execute(
        select(CartItem)
        .where(CartItem.id == cart_item.id)
        .options(selectinload(CartItem.product))
    )
    return result.scalar_one()


@router.delete("/{item_id}", status_code=204)
async def remove_from_cart(item_id: int, db: AsyncSession = Depends(get_db)):
    cart_item = await db.get(CartItem, item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    await db.delete(cart_item)
    await db.commit()
