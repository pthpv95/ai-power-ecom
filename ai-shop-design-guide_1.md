# AI E-Commerce Agent — High-Level Design Guide

> **Your background:** Fullstack JavaScript
> **Goal:** Build an interview-ready project demonstrating RAG, Agent Tool Use, and Multi-Turn Memory

---

## Mental Model: JS → Python Translation

Before anything else, here's how to map what you already know:

| You Know (JS)        | You'll Learn (Python)     | Role                    |
|----------------------|---------------------------|-------------------------|
| Express / NestJS     | **FastAPI**               | Web framework           |
| Prisma / TypeORM     | **SQLAlchemy**            | Database ORM            |
| Prisma Migrate       | **Alembic**               | DB migrations           |
| Zod                  | **Pydantic**              | Request/response validation |
| `npm` / `pnpm`      | **uv**                    | Package manager         |
| `package.json`       | `pyproject.toml`          | Project config          |
| `node_modules/`      | `.venv/`                  | Dependencies folder     |
| `nodemon`            | `uvicorn --reload`        | Dev server with hot reload |
| Next.js API Routes   | FastAPI routers           | API endpoints           |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Chat Panel   │  │ Product Grid │  │ Cart Drawer  │  │
│  │  (SSE stream) │  │ (dynamic)    │  │ (real-time)  │  │
│  └──────┬───────┘  └──────────────┘  └──────────────┘  │
│         │ SSE / REST                                    │
└─────────┼───────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                      │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │              /api/chat  (POST)                   │    │
│  │                                                  │    │
│  │  ┌───────────────────────────────────────────┐   │    │
│  │  │         LangGraph Agent Loop              │   │    │
│  │  │                                           │   │    │
│  │  │  User msg → GPT-4o decides:               │   │    │
│  │  │    ├─ Call a tool? → Execute → Loop back   │   │    │
│  │  │    └─ Respond? → Stream answer to user     │   │    │
│  │  │                                           │   │    │
│  │  │  Tools available:                         │   │    │
│  │  │    • search_products(query, filters)      │   │    │
│  │  │    • get_product_details(product_id)      │   │    │
│  │  │    • add_to_cart(user_id, product_id)     │   │    │
│  │  │    • remove_from_cart(user_id, product_id)│   │    │
│  │  │    • get_current_cart(user_id)            │   │    │
│  │  │    • compare_products(product_ids)        │   │    │
│  │  └───────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ /api/products │  │  /api/cart   │  │ /api/search  │  │
│  │   (CRUD)      │  │  (CRUD)     │  │ (semantic)   │  │
│  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘  │
└─────────┼─────────────────┼─────────────────┼──────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌──────────────────┐              ┌──────────────────┐
│   PostgreSQL     │              │    Pinecone      │
│  (AWS RDS)       │              │  (Vector DB)     │
│                  │              │                  │
│  • products      │              │  • product       │
│  • cart_items    │              │    embeddings    │
│  • messages      │              │    (semantic     │
│  • users         │              │     search)      │
└──────────────────┘              └──────────────────┘
```

---

## Build Phases (In Order)

### Phase 1: Backend Skeleton (Days 1–2)

**What to do:**
- Set up FastAPI project with `uv` (Python package manager)
- Docker Compose for local PostgreSQL
- Define SQLAlchemy models: `products`, `cart_items`, `messages`
- Build basic REST endpoints: product CRUD, cart operations
- Seed database with ~20 outdoor/hiking products (varied categories, prices, specs)

**What you'll learn:**
- FastAPI fundamentals (decorators, dependency injection, Pydantic validation)
- SQLAlchemy async ORM (equivalent of Prisma)
- Python project structure

**Done when:** You can hit `/api/products` and `/api/cart/{user_id}` and get JSON back. Swagger docs work at `/docs`.

---

### Phase 2: Frontend Shell (Days 2–3)

**What to do:**
- `create-next-app` with TypeScript + Tailwind + App Router
- Two-panel layout: Chat on the left, Product display on the right
- Chat input box with message history (just UI, no AI yet)
- Product cards component (receives products as props)
- Cart drawer/sidebar component
- Wire up REST calls to your FastAPI backend

**What you'll learn:**
- Nothing new (this is your comfort zone) — move fast here

**Done when:** You can type a message, see it in the chat. Products display from the API. Cart shows items. No AI yet — just a working UI shell.

---

### Phase 3: Semantic Search / RAG (Days 3–5)

**What to do:**
1. Write a **seed script** that generates vector embeddings for each product
   - Input: `"{name}. {description}. Category: {category}. Brand: {brand}"`
   - Model: OpenAI `text-embedding-3-small` (cheap, fast, 1536 dimensions)
   - Store vectors in Pinecone with `product_id` as metadata
2. Build a **semantic search service**:
   - Receive natural language query → embed it → query Pinecone top-k
   - Fetch full product records from PostgreSQL by returned IDs
   - Apply hard filters post-retrieval (price, category, in_stock)
3. Expose as `POST /api/search/semantic` endpoint

**Key design decision — Why Pinecone over Weaviate:**
- Simpler setup (fully managed, no self-hosting)
- Free tier covers this project easily
- More commonly asked about in interviews

**The RAG flow:**

```
User: "waterproof gear for rainy hikes under $100"
                    │
                    ▼
        ┌───────────────────┐
        │  Embed the query   │  ← OpenAI text-embedding-3-small
        └─────────┬─────────┘
                  │ vector
                  ▼
        ┌───────────────────┐
        │  Pinecone search   │  ← top_k=10, cosine similarity
        │  returns IDs +     │
        │  similarity scores │
        └─────────┬─────────┘
                  │ [id: 1, id: 5, id: 7, ...]
                  ▼
        ┌───────────────────┐
        │  PostgreSQL lookup │  ← Full product records
        │  + hard filters    │  ← WHERE price <= 100
        └─────────┬─────────┘     AND in_stock > 0
                  │
                  ▼
        Return filtered products
```

**Interview talking point:** "I use vector search for semantic recall, then SQL for hard constraints. This is the standard retrieval-then-filter RAG pattern because embedding models don't reliably encode numeric constraints like price ranges."

**Done when:** You can search "something warm for cold camping" and get sleeping bags, base layers, and jackets back — not just keyword matches.

---

### Phase 4: AI Agent with Tool Use (Days 5–8)

**This is the core of the project. Spend the most time here.**

**What to do:**
1. Install LangGraph + LangChain + OpenAI SDK
2. Define **tools** as Python functions with clear docstrings:
   - `search_products(query, max_price?, category?)` → calls your semantic search
   - `get_product_details(product_id)` → returns full specs from PostgreSQL
   - `add_to_cart(user_id, product_id, quantity)` → modifies cart
   - `remove_from_cart(user_id, product_id)` → removes item
   - `get_current_cart(user_id)` → returns cart contents + total
   - `compare_products(product_ids)` → side-by-side specs comparison
3. Build a **LangGraph agent** (not a plain LangChain AgentExecutor):

```
Agent Graph:

    ┌──────────────┐
    │  agent_node   │ ← GPT-4o with tools bound
    │  (reason)     │
    └──────┬───────┘
           │
     ┌─────┴──────┐
     │  Has tool   │
     │  call?      │
     ├─Yes─────────┤
     │             │
     ▼             ▼
┌──────────┐   ┌────────┐
│ tool_node │   │  END   │ ← Stream response to user
│ (execute) │   └────────┘
└─────┬────┘
      │ result
      └──────→ Back to agent_node (loop)
```

4. Write a **system prompt** that defines:
   - Agent persona ("You are a helpful shopping assistant...")
   - Available tools and when to use them
   - Behavioral rules (always confirm before cart changes, show prices, be concise)
5. Create `POST /api/chat` endpoint that:
   - Receives `{ user_id, message, conversation_id }`
   - Loads conversation history
   - Runs the agent graph
   - Returns response (+ any products the agent found)

**Key design decision — Why LangGraph over plain LangChain AgentExecutor:**
- Explicit control over the reasoning loop (you can see and debug each step)
- Easy to add conditional logic (e.g., "if cart total > $500, suggest a discount")
- Much more interview-discussable — you can whiteboard the graph
- AgentExecutor is a black box; LangGraph is transparent

**Example interaction flow:**

```
User: "I need gear for a rainy hike, budget is $100"

Agent thinks: I should search for relevant products
  → Calls: search_products(query="rainy hike gear", max_price=100)
  → Gets: [Rain Jacket $74.99, Hiking Boots $89.99, Headlamp $39.99]

Agent thinks: I have good results, let me present them
  → Response: "Here are some options for rainy hiking under $100:
     1. Summit Pro Rain Jacket — $74.99 (waterproof, 8oz)
     2. TrailMaster Hiking Boots — $89.99 (waterproof, Vibram sole)
     3. Black Diamond Headlamp — $39.99 (waterproof, 400 lumens)
     Want me to add any of these to your cart?"

User: "Add the jacket"

Agent thinks: User wants the rain jacket from previous results
  → Calls: add_to_cart(user_id="user_abc", product_id=5, quantity=1)
  → Response: "Done! Added the Summit Pro Rain Jacket ($74.99) to your cart."
```

**Done when:** You can have a natural conversation where the AI searches products, answers questions about specs, and manages your cart — all through chat.

---

### Phase 5: Multi-Turn Memory (Days 8–10)

**What to do:**
1. Store all messages in PostgreSQL (`messages` table with `conversation_id`)
2. On each request, load last N messages and include in the LLM prompt
3. Implement a **context window strategy**:
   - Count tokens using `tiktoken` library
   - If history exceeds ~80% of context window: summarize older messages with a separate LLM call, keep recent messages verbatim
4. Test coreference resolution ("the red ones", "that cheaper option", "add it")

**Context window management strategy:**

```
Total context window: ~128K tokens (GPT-4o)
Your budget:          ~8K tokens for history (keep it lean for cost)

┌──────────────────────────────────────┐
│ System prompt              (~500 tokens) │
│ Tool definitions           (~800 tokens) │
│ ─────────────────────────────────── │
│ Conversation summary       (~200 tokens) │  ← Older messages summarized
│ Recent messages (last 10)  (~2-4K tokens) │  ← Verbatim
│ ─────────────────────────────────── │
│ Current user message       (~100 tokens) │
└──────────────────────────────────────┘
```

**Interview talking point:** "I use a sliding window with summarization. Recent messages are kept verbatim for accuracy, older context is compressed via an LLM summary. This balances cost, latency, and context quality."

**Done when:** The agent correctly resolves "the red ones" from 3 turns ago, and conversation history persists across page refreshes.

---

### Phase 6: Streaming & UX Polish (Days 10–12)

**What to do:**
1. **Server-Sent Events (SSE)** from FastAPI → Next.js
   - FastAPI: `StreamingResponse` with `text/event-stream`
   - Next.js: `EventSource` API or `fetch` with readable stream
   - Stream token-by-token as the agent generates its response
2. **UI enhancements:**
   - Typing indicator while agent is thinking
   - "Searching products..." status when tools are being called
   - Product cards appear inline in chat when agent references them
   - Cart badge updates in real-time after agent modifies cart
   - Smooth scroll to latest message
3. **Error handling:**
   - Graceful fallback if OpenAI API fails
   - Retry logic for transient errors
   - User-friendly error messages in chat

**SSE vs WebSocket decision:**
- Use **SSE** — it's simpler, unidirectional (server → client), and sufficient since user messages go via POST. WebSocket is overkill for this use case.

**Done when:** Responses stream in word-by-word, tool executions show status indicators, and the whole experience feels smooth and responsive.

---

### Phase 7: Deployment (Days 12–14)

**Infrastructure map:**

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Vercel     │────▶│  AWS App Runner   │────▶│  AWS RDS     │
│  (Frontend)  │     │  (Backend)        │     │ (PostgreSQL) │
│  Next.js     │     │  FastAPI          │     └──────────────┘
└─────────────┘     │                    │
                    │                    │────▶┌──────────────┐
                    └──────────────────┘     │  Pinecone    │
                                             │ (Vector DB)  │
                                             └──────────────┘
```

**Step by step:**
1. **PostgreSQL** → AWS RDS free tier (or Supabase for faster setup)
2. **Pinecone** → Already managed/hosted, no deploy needed
3. **Backend** → AWS App Runner
   - Create a `Dockerfile` for the FastAPI app
   - App Runner auto-builds from a GitHub repo or ECR image
   - Set environment variables in App Runner console
   - Why App Runner over ECS: simpler (no load balancer/task definition config), auto-scales, good enough for this project
4. **Frontend** → Vercel
   - Connect GitHub repo, Vercel auto-deploys
   - Set `NEXT_PUBLIC_API_URL` env var pointing to App Runner URL

**Bonus: Observability**
- Set up **LangSmith** (free tier) to trace every agent decision
- This lets you show interviewers: "Here's the exact reasoning trace — the agent called search_products, got 5 results, then called get_product_details for the top match, then responded."

---

## Key Decisions Summary (For Interviews)

| Decision                    | Choice           | Why                                                    |
|-----------------------------|------------------|--------------------------------------------------------|
| Agent framework             | LangGraph        | Explicit control, debuggable, whiteboard-friendly      |
| Vector DB                   | Pinecone         | Managed, free tier, most asked about in interviews     |
| Embedding model             | text-embedding-3-small | Cost-effective, good quality for product search  |
| LLM                         | GPT-4o           | Best tool-use reliability, fast                        |
| Streaming                   | SSE              | Simpler than WebSocket, sufficient for chat            |
| Backend hosting             | AWS App Runner   | Simpler than ECS, auto-scales, Docker-based            |
| Frontend hosting            | Vercel           | Zero-config for Next.js                                |
| Context management          | Sliding window + summarization | Balances cost, latency, context quality |
| Post-retrieval filtering    | SQL after vector search | Embeddings can't reliably encode numeric constraints |

---

## What Interviewers Will Ask About

1. **"Why not just use keyword search?"**
   → Keywords fail on intent. "something for cold rainy weather" has zero keyword overlap with "Gore-Tex waterproof hiking jacket" but high semantic similarity.

2. **"How do you handle hallucination in product recommendations?"**
   → The agent can ONLY recommend products returned by the search tool (grounded in real DB data). It doesn't invent products. Tool outputs are the single source of truth.

3. **"What if the user asks something the agent can't handle?"**
   → System prompt includes fallback behavior. If no tool is relevant, the agent says so honestly rather than guessing. Guardrails prevent out-of-scope actions.

4. **"How would you scale this to millions of products?"**
   → Hybrid search (vector + BM25 keyword via Pinecone's sparse-dense), add a re-ranking step (Cohere reranker or cross-encoder), cache frequent queries, batch embedding generation.

5. **"Why LangGraph over a simple function-calling loop?"**
   → LangGraph gives you: state management between steps, conditional branching (e.g., ask for confirmation before expensive actions), easier testing of individual nodes, and clear observability of the decision graph.

6. **"How do you manage cost?"**
   → Small embedding model, token-aware context window management, caching repeated searches, streaming to reduce perceived latency (user starts reading while generation continues).

---

## Timeline Summary

| Phase | Days  | What                              | New Skills Learned                    |
|-------|-------|-----------------------------------|---------------------------------------|
| 1     | 1–2   | FastAPI + PostgreSQL + REST APIs  | Python, FastAPI, SQLAlchemy           |
| 2     | 2–3   | Next.js chat UI shell             | (Your comfort zone — move fast)       |
| 3     | 3–5   | Semantic search with Pinecone     | Embeddings, vector DB, RAG pattern    |
| 4     | 5–8   | LangGraph agent + tool use        | LangGraph, function calling, prompting|
| 5     | 8–10  | Multi-turn memory + context mgmt  | Token management, conversation state  |
| 6     | 10–12 | SSE streaming + UI polish         | Streaming architecture, production UX |
| 7     | 12–14 | Deploy to AWS + Vercel            | Docker, App Runner, cloud infra       |

**Total: ~14 days at 3–4 hours/day. Compress to 7–8 days if going full-time.**
