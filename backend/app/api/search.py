from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ProductResponse
from app.services.search import semantic_search

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    max_price: float | None = None
    category: str | None = None
    in_stock_only: bool = True
    top_k: int = 5


class SearchResponse(BaseModel):
    query: str
    results: list[ProductResponse]


@router.post("/semantic", response_model=SearchResponse)
async def search_products(body: SearchRequest, db: AsyncSession = Depends(get_db)):
    products = await semantic_search(
        query=body.query,
        db=db,
        max_price=body.max_price,
        category=body.category,
        in_stock_only=body.in_stock_only,
        top_k=body.top_k,
    )
    return SearchResponse(query=body.query, results=products)
