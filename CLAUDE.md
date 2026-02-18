# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered e-commerce shopping assistant. A chat-based agent that can search products semantically, manage a shopping cart, and maintain multi-turn conversation context.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy (async ORM), Alembic (migrations), uv (package manager)
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS
- **AI/ML:** LangGraph agent with GPT-4o, OpenAI text-embedding-3-small for embeddings
- **Databases:** PostgreSQL (products, cart_items, messages, users), Pinecone (vector embeddings for semantic search)
- **Streaming:** Server-Sent Events (SSE) from FastAPI to Next.js
- **Deployment:** Vercel (frontend), AWS App Runner (backend), AWS RDS (PostgreSQL)

## Architecture

Two-service architecture: Next.js frontend communicates with FastAPI backend via REST + SSE.

**Core flow:** User message → `POST /api/chat` → LangGraph agent loop (GPT-4o decides whether to call tools or respond) → SSE stream response back.

**Agent tools:** `search_products`, `get_product_details`, `add_to_cart`, `remove_from_cart`, `get_current_cart`, `compare_products`

**RAG pattern:** Natural language query → embed with text-embedding-3-small → Pinecone cosine similarity search (top-k) → fetch full records from PostgreSQL → apply hard filters (price, category, stock) in SQL. Vector search handles semantic recall; SQL handles numeric constraints.

**Context management:** Sliding window with summarization. Recent messages kept verbatim, older messages compressed via LLM summary. Token counting with tiktoken, budget ~8K tokens for history.

## Build Phases

The project follows 7 phases (see `ai-shop-design-guide_1.md` for full details):
1. Backend skeleton (FastAPI + PostgreSQL + REST)
2. Frontend shell (Next.js chat UI)
3. Semantic search / RAG (Pinecone + embeddings)
4. AI agent with tool use (LangGraph)
5. Multi-turn memory
6. Streaming & UX polish (SSE)
7. Deployment

## Key Commands (once project is set up)

```bash
# Backend
uv run uvicorn app.main:app --reload        # Dev server
uv run alembic upgrade head                  # Run migrations
uv run alembic revision --autogenerate -m "" # Generate migration

# Frontend
npm run dev                                  # Next.js dev server

# Local services
docker compose up -d                         # PostgreSQL
```

## Key Design Decisions

- **LangGraph over AgentExecutor:** Explicit control over reasoning loop, conditional branching, debuggable nodes
- **Pinecone over Weaviate:** Managed, free tier, simpler setup
- **SSE over WebSocket:** Simpler, unidirectional server→client is sufficient for chat
- **Post-retrieval filtering:** Embeddings can't reliably encode numeric constraints, so filter in SQL after vector search
- **Agent grounding:** Agent can only recommend products returned by search tools (prevents hallucinated products)
