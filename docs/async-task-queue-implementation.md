# Async Task Queue — Implementation Details

## Overview

Decoupled the agent loop from the HTTP request handler using **Redis Streams + Arq**. The API server now returns immediately (~100ms) after enqueuing the job. A separate Arq worker runs the LLM + tool-call loop and publishes events to a Redis Stream, which the SSE endpoint relays to the client.

## Files Created

| File | Purpose |
|------|---------|
| `backend/app/redis_client.py` | Shared async Redis connection pool (lazy singleton, `decode_responses=True`) |
| `backend/app/worker.py` | Arq worker with `run_agent_task()` — the extracted agent loop |

## Files Modified

| File | Change |
|------|--------|
| `docker-compose.yml` | Added `redis:7-alpine` service with persistent volume |
| `backend/pyproject.toml` | Added `arq>=0.26.0` and `redis>=5.0.0` |
| `backend/app/config.py` | Added `redis_url` setting (default `redis://localhost:6379`) |
| `backend/app/main.py` | Added FastAPI lifespan for graceful Redis shutdown |
| `backend/app/api/chat.py` | `POST /stream` → enqueue + return JSON; new `GET /events/{id}` SSE reader |
| `frontend/src/api/index.ts` | Two-step flow: POST for `conversation_id`, then fetch SSE from `/events/` |

## Key Implementation Details

### Worker (`app/worker.py`)
- Uses `SessionLocal()` directly (not FastAPI's `Depends(get_db)`) since it runs outside the request lifecycle
- Sets `db_var` / `user_id_var` ContextVars at task start — same mechanism as the old request handler, works because each Arq task is a separate coroutine
- Publishes events via `redis.xadd(stream_key, {"data": json.dumps(event)})` instead of `yield sse_event()`
- Sets `EXPIRE stream:{request_id} 3600` after done event — auto-cleanup
- Uses `_job_id=request_id` to prevent double-submit of the same message (see Bug Fix below)
- `max_tries=2` for transient failure recovery

### SSE Endpoint (`GET /events/{request_id}`)
- Uses `XREAD BLOCK` with 15-second intervals for keepalive
- Sends `:keepalive\n\n` SSE comments to prevent proxy/browser timeouts
- Total timeout of 60s (4 intervals × 15s) if no events arrive
- Supports reconnect via `?last_id=` query param — resumes from that Redis Stream ID
- Closes after receiving `done` or `error` event

### Frontend (`streamChatMessage`)
- Step 1: `POST /api/chat/stream` → get `{ conversation_id, request_id, status: "queued" }`
- Step 2: `fetch(/api/chat/events/${requestId})` → read SSE via ReadableStream
- Same callback interface (`onToken`, `onStatus`, `onDone`, `onError`, `onCartUpdated`) — `ChatPanel.tsx` requires zero changes
- Now also handles `error` event type from the stream

### Redis Connection Pool
- Lazy singleton pattern — created on first `get_redis()` call
- `decode_responses=True` so all values come back as strings (not bytes)
- Closed gracefully via FastAPI lifespan on shutdown

## Running Locally

```bash
docker compose up -d                           # PostgreSQL + Redis
uv run uvicorn app.main:app --reload           # Terminal 1: API server
uv run arq app.worker.WorkerSettings           # Terminal 2: Arq worker
npm run dev                                    # Terminal 3: Frontend
```

## Bug Fix: Duplicate AI Messages on 2nd+ Chat Message

### Symptom
First message in a conversation worked fine. Every subsequent message rendered duplicate AI responses — the frontend replayed the previous message's tokens.

### Root Cause
Two issues caused by keying both the Arq job ID and Redis Stream on `conversation_id`:

1. **Arq job deduplication blocked new messages.** `_job_id=conversation_id` meant Arq treated the 2nd message as a duplicate of the 1st (same job ID, result still cached in Redis within `keep_result` window). The worker never picked up the 2nd message.

2. **Redis Stream replayed old events.** `stream:{conversation_id}` was shared across all messages in the same conversation. The SSE reader on the 2nd request started from `0-0` and replayed all events from the 1st message's stream.

### Fix
Introduced a per-message `request_id` (UUID) separate from `conversation_id`:

| Before | After |
|--------|-------|
| `_job_id=conversation_id` | `_job_id=request_id` |
| `stream:{conversation_id}` | `stream:{request_id}` |
| Response: `{ conversation_id }` | Response: `{ conversation_id, request_id }` |
| SSE: `GET /events/{conversation_id}` | SSE: `GET /events/{request_id}` |

- `conversation_id` — identifies the conversation (shared across messages, used for DB queries)
- `request_id` — identifies a single user message (unique per request, used for job dedup + stream isolation)

### Takeaway
When using Redis Streams as a per-request event bus, the stream key must be scoped to the **request**, not the **session/conversation**. Session-scoped keys cause event replay on subsequent requests. Similarly, Arq's `_job_id` should match the dedup granularity you actually want — per-message, not per-conversation.

## Lessons Learned

1. **ContextVars work across process boundaries** — as long as you set them at the top of each coroutine (Arq task), they propagate to all nested `await` calls. The key insight: ContextVars are scoped to the coroutine, not the process.

2. **Redis Streams > Pub/Sub for SSE** — Pub/Sub drops messages if no subscriber is listening at that instant. Streams are a persistent log, so clients can disconnect and reconnect with `last_id` without losing tokens. This is critical for mobile or flaky connections.

3. **SSE keepalive is essential** — without periodic heartbeat comments (`:keepalive\n\n`), reverse proxies (nginx, CloudFront, ALB) and browsers will kill idle SSE connections after 30-60s. The 15s interval is a sweet spot.

4. **Arq's `_job_id` must match your dedup granularity** — use a per-message `request_id`, not `conversation_id`. Using `conversation_id` blocks all subsequent messages in the same conversation because Arq sees them as duplicates of the completed first job.

5. **Lazy-init connection pools** — both the Redis pool and the Arq pool are initialized on first use, not at import time. This avoids connection errors during module loading (e.g., `uv run alembic` doesn't need Redis).

6. **`decode_responses=True` on Redis client** — without this, `XREAD` returns bytes (`b'data'`) instead of strings, causing `json.loads()` to fail or return unexpected types. Always set this for application-level Redis usage.
