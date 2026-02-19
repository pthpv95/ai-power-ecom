from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.products import router as products_router
from app.api.cart import router as cart_router
from app.api.search import router as search_router
from app.api.chat import router as chat_router

app = FastAPI(title="AI Shop API", version="0.1.0")

app.include_router(health_router, prefix="/api")
app.include_router(products_router, prefix="/api/products", tags=["products"])
app.include_router(cart_router, prefix="/api/cart", tags=["cart"])
app.include_router(search_router, prefix="/api/search", tags=["search"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
