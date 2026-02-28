# Async Task Queue for Chat Processing

## Problem

Currently, the entire agent loop (LLM calls, tool execution, token streaming) runs **inside** the HTTP request handler in `app/api/chat.py`. This means:

- The API server is blocked for the full duration of agent processing (5–30+ seconds per request)
- Under load, API workers are tied up waiting on OpenAI, limiting concurrent users
- If the API process restarts mid-stream, the response is lost

## Goal

Decouple "receive the request" (fast, ~100ms) from "run the agent" (slow, 5–30s) so the API server can handle more concurrent requests and the agent processing can scale independently.

---

## Current Flow (Synchronous)

```
POST /api/chat/stream  { user_id, message, conversation_id }
  │
  ├── Validate message length
  ├── Set ContextVars (db_var, user_id_var)
  ├── save_message(db, "user", message)              ← PostgreSQL write
  ├── load_messages(db, conversation_id)              ← PostgreSQL read
  ├── build_context(db_messages)                      ← token count + maybe OpenAI summarize
  │
  └── StreamingResponse(event_generator())
        │
        └── while True:
              ├── llm_with_tools.ainvoke(messages)    ← OpenAI API call
              ├── IF tool_calls:
              │     ├── yield SSE "status" event
              │     ├── tool_fn.ainvoke(args)          ← DB + Pinecone + OpenAI
              │     ├── yield SSE "cart_updated" (if cart mutation)
              │     └── continue loop
              └── ELSE (final answer):
                    ├── llm_with_tools.astream()       ← OpenAI streaming
                    ├── yield SSE "token" events
                    └── break
        │
        ├── save_message(db, "assistant", response)   ← PostgreSQL write
        └── yield SSE "done" event
```

Everything runs in the same HTTP request — the connection stays open for the full 5–30s of agent processing.

---

## Proposed Architecture (Async)

```
Client (Next.js)
  │
  ├─ POST /api/chat/stream
  │    → API validates, saves user msg, enqueues Arq job
  │    → Returns { conversation_id, status: "queued" }   (~100ms)
  │
  └─ GET /api/chat/events/{conversation_id}
       → SSE stream
       → API subscribes to Redis Stream, forwards events to client
                                              ↑
                                              │ XADD events
                                              │
                                     Arq Worker Process
                                     (runs agent loop,
                                      publishes events to Redis Stream)
```

### Technology Choices

| Technology | Why |
|------------|-----|
| **Redis Streams** (not Pub/Sub) | Persistent log — clients can reconnect without losing tokens. Pub/Sub drops messages if no subscriber is listening at that instant. |
| **Arq** (not Celery) | Lightweight, async-native task queue using Redis. Celery is sync-first and requires `asyncio.run()` wrappers. |
| **redis-py** (`redis.asyncio`) | Async Redis client included in the `redis` package. |

### Why Redis Streams over Pub/Sub

| Concern | Pub/Sub | Streams |
|---------|---------|---------|
| Client drops connection for 2s | Tokens lost permanently | Client reconnects with `last_id`, gets all missed messages |
| Worker crashes mid-response | Client hangs forever | Client times out on `XREAD BLOCK`, emits error |
| Multiple API instances | Each subscribes independently | Each reads with their own cursor |
| Message replay for debugging | Impossible | `XRANGE stream:abc 0 +` shows everything |

---

## Detailed Design

### New Endpoint Flow

#### `POST /api/chat/stream` (modified)

```
1. Validate input (message length)
2. Save user message to PostgreSQL
3. Enqueue run_agent_task via Arq
   - _job_id=conversation_id  (prevents duplicate processing on double-submit)
4. Return { conversation_id, status: "queued" }
```

Response is immediate (~100ms). The API worker is freed up.

#### `GET /api/chat/events/{conversation_id}` (new)

```
1. Open Redis connection
2. XREAD BLOCK on stream:{conversation_id}
3. For each message in the stream:
   - Parse the event data
   - Yield as SSE (same format: status, token, cart_updated, done)
4. Accept optional ?last_id= query param for reconnect/resume
5. Close connection after "done" event or 60s timeout
```

SSE event format stays identical to the current implementation:
```
data: {"type": "token", "content": "Hello"}\n\n
data: {"type": "status", "content": "Searching products..."}\n\n
data: {"type": "cart_updated"}\n\n
data: {"type": "done", "conversation_id": "abc-123"}\n\n
```

### Arq Worker

The worker extracts the agent loop from `chat.py`'s `event_generator()`. Instead of `yield sse_event(...)`, it writes to Redis Stream via `XADD`.

```python
async def run_agent_task(ctx, *, conversation_id: str, user_id: str):
    redis = ctx["redis"]
    stream_key = f"stream:{conversation_id}"

    async with SessionLocal() as db:
        db_var.set(db)           # ContextVars work within worker's async scope
        user_id_var.set(user_id)

        db_messages = await load_messages(db, conversation_id)
        messages = await build_context(db_messages)

        # ... same while True agent loop as chat.py ...
        # But: await redis.xadd(stream_key, {"data": json.dumps(event)})
        # Instead of: yield sse_event(event)

        await save_message(db, conversation_id, "assistant", full_response)

    await redis.expire(stream_key, 3600)  # auto-cleanup after 1 hour
```

**Why ContextVars still work:** Each Arq task runs as a separate coroutine in the worker's event loop. `db_var.set(db)` at the top of the task propagates to all `await` calls within that coroutine's scope — including deep inside `tool_fn.ainvoke()`. This is the same mechanism FastAPI's request handler uses.

---

## Files to Create/Modify

### New files

| File | Purpose |
|------|---------|
| `app/redis_client.py` | Async Redis connection pool, shared by API server and worker |
| `app/worker.py` | Arq worker definition: `run_agent_task`, `WorkerSettings`, startup/shutdown hooks |

### Modified files

| File | Change |
|------|--------|
| `app/config.py` | Add `redis_url: str` setting (default: `redis://localhost:6379`) |
| `app/api/chat.py` | `POST /stream` → enqueue + return JSON; new `GET /events/{id}` SSE endpoint |
| `docker-compose.yml` | Add Redis service |
| `pyproject.toml` | Add `arq>=0.26.0` and `redis>=5.0.0` |

### Unchanged files (and why)

| File | Why unchanged |
|------|---------------|
| `app/agent/graph.py` | Agent logic stays the same — worker imports and uses it |
| `app/agent/tools.py` | Tools unchanged — ContextVars work in the worker process |
| `app/agent/context.py` | ContextVars work identically across processes |
| `app/services/conversation.py` | `save_message`/`load_messages` are stateless, only need a DB session |
| `app/services/context_manager.py` | `build_context` is stateless, reusable from worker |

---

## Implementation Steps

### Step 1: Infrastructure — Redis + dependencies
- Add Redis to `docker-compose.yml`
- Add `redis_url` to `app/config.py`
- Create `app/redis_client.py` with async connection pool
- Add `arq>=0.26.0` and `redis>=5.0.0` to `pyproject.toml`

### Step 2: Worker — extract agent loop
- Create `app/worker.py`
- Extract `event_generator()` logic from `chat.py` into `run_agent_task()`
- Replace `yield sse_event(...)` with `await redis.xadd(...)`
- Worker manages its own DB sessions via `SessionLocal()`
- Define `WorkerSettings` with startup/shutdown hooks

### Step 3: Rewrite chat endpoints
- `POST /api/chat/stream` → validate, save user msg, enqueue, return JSON
- New `GET /api/chat/events/{conversation_id}` → subscribe to Redis Stream, forward as SSE
- Keep `POST /api/chat` (non-streaming) as-is for Swagger testing

### Step 4: Stream lifecycle & error handling
- Worker sets `EXPIRE stream:{conversation_id} 3600` after `done` event
- SSE endpoint times out after 60s of no data (worker crash protection)
- Arq `_job_id=conversation_id` prevents duplicate processing
- Arq retry: `_retry_limit=1` for transient failures

### Step 5: Frontend update
- `POST /api/chat/stream` → read `conversation_id` from JSON response
- Open `EventSource` to `GET /api/chat/events/{conversation_id}`
- SSE event format is identical — no parsing changes needed

---

## Frontend Impact

Small change in the Next.js client:

**Before:**
```js
const response = await fetch('/api/chat/stream', { method: 'POST', body: ... });
const reader = response.body.getReader();  // SSE from POST response
```

**After:**
```js
const response = await fetch('/api/chat/stream', { method: 'POST', body: ... });
const { conversation_id } = await response.json();

const eventSource = new EventSource(`/api/chat/events/${conversation_id}`);
eventSource.onmessage = (e) => { /* same event handling */ };
```

SSE event types (`status`, `token`, `cart_updated`, `done`) are unchanged.

---

## Running Locally

```bash
# Start services
docker compose up -d   # PostgreSQL + Redis

# Terminal 1: API server
uv run uvicorn app.main:app --reload

# Terminal 2: Arq worker
uv run arq app.worker.WorkerSettings
```

---

## AWS Deployment Options

**Option A: Two App Runner services (recommended for scaling)**
- Service 1: API server (`uvicorn app.main:app`)
- Service 2: Arq worker (`arq app.worker.WorkerSettings`)
- Both share RDS PostgreSQL + ElastiCache Redis

**Option B: Single container with supervisord (simpler for solo dev)**
- Run both uvicorn and arq in one container
- Simpler operationally, loses independent scaling

---

## Verification Checklist

1. `docker compose up -d` — confirm Redis running alongside PostgreSQL
2. Start API server and worker in separate terminals
3. `POST /api/chat/stream` → returns `{ conversation_id, status: "queued" }` immediately
4. `GET /api/chat/events/{conversation_id}` → receives SSE events from worker
5. Full agent flow: status events during tool calls → token streaming → done
6. Cart mutations trigger `cart_updated` events
7. Reconnect test: disconnect mid-stream, reconnect with `?last_id=` → resumes without lost tokens
8. `POST /api/chat` (non-streaming) still works unchanged
9. Worker crash: SSE endpoint times out gracefully after 60s

---

## Status

- [ ] Step 1: Infrastructure (Redis + dependencies)
- [ ] Step 2: Worker (extract agent loop)
- [ ] Step 3: Rewrite chat endpoints
- [ ] Step 4: Stream lifecycle & error handling
- [ ] Step 5: Frontend update
