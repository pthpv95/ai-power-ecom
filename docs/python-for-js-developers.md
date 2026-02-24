# Python & FastAPI for JavaScript Developers

A comprehensive reference mapping JS/TS knowledge to the Python stack used in this project.

---

## Libraries Overview

| Library | JS Equivalent | Role |
|---------|--------------|------|
| **FastAPI** | Express / NestJS | Web framework with auto-generated Swagger docs |
| **SQLAlchemy** | Prisma / TypeORM | Async ORM with type-safe models |
| **Alembic** | Prisma Migrate | DB schema migrations |
| **Pydantic** | Zod | Request/response validation via type hints |
| **pydantic-settings** | `dotenv` + Zod | Typed env config with `.env` loading |
| **uvicorn** | nodemon | ASGI dev server with hot reload |
| **asyncpg** | `pg` / `node-postgres` | Async PostgreSQL driver |
| **LangGraph** | — | Graph-based agent framework (explicit control flow) |
| **langchain-core** | — | Tool definitions, message types |
| **langchain-openai** | `openai` npm | OpenAI LLM + embeddings integration |
| **openai** | `openai` npm | Direct embedding API calls |
| **pinecone** | `@pinecone-database/pinecone` | Vector DB client |
| **tiktoken** | `tiktoken` (npm) | Token counting for context management |
| **httpx** | `supertest` / `axios` | Async HTTP client for testing |
| **pytest** | Jest / Vitest | Test framework |
| **pytest-asyncio** | — | Async test support |

---

## Syntax Cheatsheet: JS → Python

### 1. Imports

```javascript
// JS
import { Router } from 'express'
import { z } from 'zod'
```

```python
# Python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
```

### 2. Variables & Types

```javascript
// JS/TS
const name: string = "hello"
let price: number | null = null
```

```python
# Python — type hints are optional but used everywhere in this project
name: str = "hello"
price: float | None = None  # Python 3.10+ union syntax
```

### 3. Async/Await (almost identical!)

```javascript
// JS
async function getProduct(id) {
  const result = await db.query('SELECT * FROM products WHERE id = $1', [id])
  return result.rows[0]
}
```

```python
# Python
async def get_product(product_id: int, db: AsyncSession):
    product = await db.get(Product, product_id)
    return product
```

### 4. Arrow Functions → Lambda / Regular Functions

```javascript
// JS
const double = (x) => x * 2
const items = products.map(p => p.name)
```

```python
# Python — lambdas are single-expression only
double = lambda x: x * 2
items = [p.name for p in products]  # list comprehension (preferred)
```

### 5. Destructuring → Unpacking

```javascript
// JS
const { name, price } = product
const [first, ...rest] = items
```

```python
# Python — dict unpacking with **
product = Product(**body.model_dump())  # spreads dict into kwargs

first, *rest = items  # star unpacking
```

### 6. Template Literals → F-strings

```javascript
// JS
const msg = `Product: ${name} — $${price.toFixed(2)}`
```

```python
# Python
msg = f"Product: {name} — ${price:.2f}"  # :.2f = 2 decimal places
```

### 7. `.map()` / `.filter()` → List Comprehensions

```javascript
// JS
const names = products.map(p => p.name)
const cheap = products.filter(p => p.price < 50)
const total = items.reduce((sum, i) => sum + i.price * i.qty, 0)
```

```python
# Python — comprehensions are more idiomatic
names = [p.name for p in products]
cheap = [p for p in products if p.price < 50]
total = sum(item.price * item.qty for item in items)  # generator expression
```

### 8. Dict Comprehensions (no JS equivalent)

```python
# Build a lookup map from a list
TOOL_MAP = {t.name: t for t in ALL_TOOLS}
products_by_id = {p.id: p for p in result.scalars().all()}
```

### 9. `try/catch` → `try/except`

```javascript
// JS
try {
  await doSomething()
} catch (error) {
  console.error(error)
}
```

```python
# Python
try:
    await do_something()
except Exception as e:
    logger.error(f"Error: {e}")
```

---

## Key FastAPI Patterns

### Route Definitions (Express → FastAPI)

```javascript
// Express
router.get('/products/:id', async (req, res) => {
  const product = await getProduct(req.params.id)
  if (!product) return res.status(404).json({ detail: 'Not found' })
  res.json(product)
})
```

```python
# FastAPI — decorators define routes, type hints auto-validate
@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product  # auto-serialized via Pydantic's response_model
```

Key differences:
- **Path params** are function args with type hints (auto-validated)
- **`response_model`** auto-serializes the return value
- **`Depends()`** is dependency injection (like NestJS providers)

### Dependency Injection (NestJS → FastAPI)

```javascript
// NestJS
@Injectable()
class DbService { ... }

@Controller('products')
class ProductsController {
  constructor(private db: DbService) {}
}
```

```python
# FastAPI — functions as dependencies, injected via Depends()
async def get_db():
    async with SessionLocal() as session:
        yield session  # yield = "return then cleanup"

@router.get("/")
async def list_products(db: AsyncSession = Depends(get_db)):
    # db is auto-injected by FastAPI
    result = await db.execute(select(Product))
    return result.scalars().all()
```

### Pydantic Models (Zod → Pydantic)

```javascript
// Zod
const ProductSchema = z.object({
  name: z.string(),
  price: z.number(),
  category: z.string().optional(),
})
```

```python
# Pydantic — class-based, type hints drive validation
class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    category: str
    image_url: str | None = None  # optional field

    model_config = {"from_attributes": True}  # enables SQLAlchemy → Pydantic conversion
```

---

## SQLAlchemy Patterns (Prisma → SQLAlchemy)

### Model Definition

```javascript
// Prisma
model Product {
  id          Int      @id @default(autoincrement())
  name        String
  price       Decimal
  category    String
  cart_items  CartItem[]
}
```

```python
# SQLAlchemy 2.0 — Mapped type hints
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))

    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="product")
```

### CRUD Operations

```javascript
// Prisma
const products = await prisma.product.findMany({ where: { price: { lte: 100 } } })
await prisma.cartItem.create({ data: { userId, productId, quantity } })
```

```python
# SQLAlchemy async
result = await db.execute(select(Product).where(Product.price <= 100))
products = result.scalars().all()

cart_item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
db.add(cart_item)
await db.commit()
```

### Eager Loading (Prisma `include` → `selectinload`)

```javascript
// Prisma
await prisma.cartItem.findMany({ where: { userId }, include: { product: true } })
```

```python
# SQLAlchemy
result = await db.execute(
    select(CartItem)
    .where(CartItem.user_id == user_id)
    .options(selectinload(CartItem.product))  # loads product in same query
)
```

---

## LangGraph Agent Pattern

This is the most unique part — no direct JS equivalent:

```python
# 1. Define state shape (like a Redux store)
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # add_messages = reducer that appends

# 2. Define nodes (functions that transform state)
async def agent_node(state: AgentState) -> dict:
    response = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}

async def tool_node(state: AgentState) -> dict:
    last = state["messages"][-1]
    results = []
    for tc in last.tool_calls:
        result = await TOOL_MAP[tc["name"]].ainvoke(tc["args"])
        results.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
    return {"messages": results}

# 3. Define routing logic (conditional edges)
def should_continue(state: AgentState) -> str:
    if state["messages"][-1].tool_calls:
        return "tools"
    return "end"

# 4. Build the graph
graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
graph.add_edge("tools", "agent")  # after tools → back to agent
agent = graph.compile()
```

### Tool Definitions (decorator extracts schema from type hints + docstring)

```python
@tool
async def search_products(
    query: str,
    max_price: float | None = None,
    category: str | None = None,
) -> str:
    """Search for products by natural language query.
    Use this when the user asks about products or gear recommendations.
    """
    db = db_var.get()  # context variable (explained below)
    products = await semantic_search(query=query, db=db, max_price=max_price)
    return "\n\n".join(format_product(p) for p in products)
```

### Context Variables (like AsyncLocalStorage in Node.js)

```python
# Python's contextvars = Node's AsyncLocalStorage
from contextvars import ContextVar

db_var: ContextVar[AsyncSession] = ContextVar("db")
user_id_var: ContextVar[str] = ContextVar("user_id")

# Set in endpoint handler
db_var.set(db)
user_id_var.set(body.user_id)

# Read anywhere in the call stack (no need to pass as args)
db = db_var.get()
user_id = user_id_var.get()
```

---

## SSE Streaming (EventSource → StreamingResponse)

```javascript
// JS consumer (frontend)
const eventSource = new EventSource('/api/chat/stream')
eventSource.onmessage = (e) => console.log(JSON.parse(e.data))
```

```python
# Python producer (backend) — async generator pattern
@router.post("/stream")
async def chat_stream(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    async def event_generator():
        yield f"data: {json.dumps({'type': 'status', 'content': 'Thinking...'})}\n\n"
        # ... agent loop streams tokens ...
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## Testing (Jest → pytest)

```javascript
// Jest
describe('GET /products', () => {
  it('returns all products', async () => {
    const res = await request(app).get('/api/products')
    expect(res.status).toBe(200)
    expect(res.body).toBeInstanceOf(Array)
  })
})
```

```python
# pytest — no describe/it blocks, just async functions prefixed with test_
async def test_list_products(client):
    response = await client.get("/api/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

Fixtures replace `beforeEach`/`afterEach`:

```python
@pytest_asyncio.fixture
async def db():
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn)
        yield session          # test runs here
        await trans.rollback()  # auto-cleanup after each test
```

### Dependency Override for Testing

```python
# tests/conftest.py — swap real DB for test DB
@pytest_asyncio.fixture
async def client(db: AsyncSession):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
```
