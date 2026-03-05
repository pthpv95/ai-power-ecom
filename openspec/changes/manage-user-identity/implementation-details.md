# Implementation Details: manage-user-identity

## Files Changed

### New Files
- `frontend/src/lib/user.ts` — Guest user ID generation + localStorage persistence
- `backend/app/api/users.py` — `ensure_user_exists()` lazy upsert helper
- `backend/alembic/versions/a1b2c3d4e5f6_add_users_table_and_user_id_to_messages.py` — Migration

### Modified Files
- `backend/app/models.py` — Added `User` model, added `user_id` column to `Message`
- `backend/app/api/cart.py` — Added ownership validation to DELETE/PATCH, lazy user creation on add
- `backend/app/api/chat.py` — Added user_id to save_message calls, conversation ownership check on GET messages
- `backend/app/services/conversation.py` — `save_message()` now accepts optional `user_id` param
- `backend/app/worker.py` — Passes `user_id` when saving assistant messages
- `frontend/src/api/index.ts` — Replaced hardcoded `user_abc` with `getUserId()` calls
- `backend/tests/test_cart.py` — Added ownership validation tests
- `backend/tests/test_integration.py` — Added user creation and conversation access tests

## Key Implementation Decisions

1. **Guest ID format**: `guest_<uuid-v4>` — the prefix makes it easy to distinguish from future authenticated IDs
2. **Lazy user creation**: No separate registration endpoint. Users are auto-created on first cart add or chat message via `ensure_user_exists()`
3. **Ownership validation approach**: Cart DELETE/PATCH now require `user_id` as a query parameter. The endpoint filters by both `item_id` AND `user_id`, returning 404 if no match (doesn't leak existence info)
4. **Conversation ownership**: `GET /messages` checks if any message in the conversation belongs to the requesting user
5. **SSR safety**: `getUserId()` returns a fallback `'guest_ssr'` during server-side rendering to avoid localStorage errors

## Migration Notes

- Run `uv run alembic upgrade head` to apply the migration
- The `messages.user_id` column is nullable to handle existing data (old messages will have NULL user_id)
- No data migration needed — old messages without user_id will still be accessible

## Lessons Learned

1. **Query param vs body for ownership**: For DELETE requests (which have no body), passing `user_id` as a query parameter is the cleanest approach. FastAPI automatically parses query params when they're function parameters not found in the path or body schema.

2. **Lazy upsert pattern**: Using `SELECT + INSERT if not found` (instead of `INSERT ... ON CONFLICT`) is simpler with SQLAlchemy ORM and sufficient when race conditions are unlikely (guest IDs are UUID-based, so collisions are practically impossible).

3. **Conversation ownership check**: Rather than adding a separate `conversations` table with an `owner_id`, we validate ownership by checking if any message in the conversation has the requesting user's `user_id`. This avoids a new table while still providing access control.

4. **Import placement matters**: In TypeScript files, imports must be at the top of the file before any exports/declarations. When using Edit to insert imports, be careful about where in the file they land.

5. **SSR considerations**: Next.js with App Router can render components server-side where `localStorage` is unavailable. Always guard browser-only APIs with `typeof window === 'undefined'` checks.
