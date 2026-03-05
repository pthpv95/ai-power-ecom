## Context

The application currently hardcodes `user_abc` as the user identity in `frontend/src/api/index.ts`. All API calls share this single identity, meaning every browser session sees the same cart and chat history. The backend already supports per-user cart isolation via `cart_items.user_id` (string column, no FK), and agent tools retrieve `user_id` from Python `contextvars`. However, there is no `users` table, no `user_id` on the `messages` table, and no ownership validation on delete/update endpoints.

## Goals / Non-Goals

**Goals:**
- Each browser session gets a unique, persistent guest identity (survives page refresh)
- Backend tracks guest users in a `users` table
- Cart and conversation resources are isolated per user
- Ownership validation on mutating endpoints (cart delete/update, conversation access)

**Non-Goals:**
- Full authentication (email/password, OAuth, JWT) — future phase
- User profiles, display names, or account settings
- Server-side sessions or cookie-based auth
- Rate limiting per user

## Decisions

### 1. Guest ID generation: UUID v4 in the browser

**Choice:** Generate a `guest_<uuid>` string in the frontend, store in `localStorage`.

**Rationale:** Simple, no server round-trip needed for ID generation. UUID v4 provides sufficient uniqueness. The `guest_` prefix makes it easy to distinguish from future authenticated user IDs.

**Alternative considered:** Server-generated ID via `POST /api/users/guest` — adds a blocking request before the app can load. Rejected for simplicity.

### 2. Backend user record: Lazy creation via upsert

**Choice:** When the frontend sends a request with a `user_id`, the backend creates a `users` row if it doesn't exist (upsert pattern). No separate registration endpoint needed.

**Rationale:** Avoids a mandatory "register guest" call on app startup. The first cart or chat request auto-creates the user. Keeps the frontend simple — just send the ID.

**Alternative considered:** Explicit `POST /api/users/guest` endpoint — adds complexity and a required startup call. Rejected.

### 3. User ID storage: `localStorage` with a helper module

**Choice:** Create a `frontend/src/lib/user.ts` module that exports `getUserId()`. On first call, generates `guest_<uuid>`, stores in `localStorage`, and returns it. Subsequent calls return the stored value.

**Rationale:** Centralizes user ID logic. All API functions import from one place. Easy to swap out for real auth later.

### 4. Messages table: Add `user_id` column

**Choice:** Add a `user_id` string column to `messages` table. Set it when saving messages. Filter conversations by user_id.

**Rationale:** Currently any conversation_id can be accessed by anyone. Adding user_id enables ownership validation.

### 5. Ownership validation: Middleware-free, per-endpoint checks

**Choice:** Add ownership checks directly in cart and chat route handlers (query includes `user_id` in WHERE clause).

**Rationale:** With only 4-5 endpoints needing protection, a middleware abstraction is premature. Direct checks are simpler and more explicit.

**Alternative considered:** FastAPI dependency that extracts and validates user_id from a header — reasonable but over-engineered for guest IDs with no auth token to validate.

### 6. User ID transport: Keep in request body/path (no auth header)

**Choice:** Continue passing `user_id` in request bodies and URL paths as currently done.

**Rationale:** No authentication means no token to put in a header. The current pattern works. When real auth is added later, this will shift to extracting user_id from a JWT in an `Authorization` header.

## Risks / Trade-offs

- **[User impersonation]** → Any client can send any user_id. Acceptable for guest identity; real auth will fix this later. Mitigation: UUID v4 makes guessing other user IDs practically impossible.
- **[localStorage cleared]** → User loses their identity and gets a new one. Cart and history are "lost" (still in DB). Acceptable for guest experience. Mitigation: none needed — this is expected behavior for anonymous users.
- **[No conversation cleanup]** → Orphaned guest user records accumulate. Mitigation: future cleanup job can purge guests with no activity for N days.
- **[Migration on messages table]** → Adding `user_id` to existing messages rows — set to empty string or NULL for legacy data. Mitigation: make column nullable, only enforce for new messages.
