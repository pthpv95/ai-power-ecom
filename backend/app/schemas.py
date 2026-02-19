from datetime import datetime

from pydantic import BaseModel


# ── Products ──────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    brand: str
    stock: int = 0
    image_url: str | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category: str
    brand: str
    stock: int
    image_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Cart ──────────────────────────────────────────────────────────────────────

class CartItemAdd(BaseModel):
    user_id: str
    product_id: int
    quantity: int = 1


class CartItemResponse(BaseModel):
    id: int
    user_id: str
    product_id: int
    quantity: int
    product: ProductResponse

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total: float


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    id: int
    conversation_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
