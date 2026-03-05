## 1. Backend: User Model & Migration

- [x] 1.1 Add `User` model to `backend/app/models.py` with `id` (String PK) and `created_at` columns
- [x] 1.2 Add `user_id` column (String, nullable) to the `Message` model in `backend/app/models.py`
- [x] 1.3 Generate Alembic migration for `users` table and `messages.user_id` column
- [ ] 1.4 Run migration and verify schema (DB not running locally — run manually with `uv run alembic upgrade head`)

## 2. Backend: Lazy User Creation

- [x] 2.1 Create a helper `ensure_user_exists(db, user_id)` in `backend/app/api/users.py` that upserts a user record
- [x] 2.2 Call `ensure_user_exists` in cart `add_to_cart` endpoint
- [x] 2.3 Call `ensure_user_exists` in chat `chat_stream` and `chat` endpoints

## 3. Backend: Ownership Validation

- [x] 3.1 Update `DELETE /api/cart/{item_id}` to require `user_id` param and validate ownership (return 404 if mismatch)
- [x] 3.2 Update `PATCH /api/cart/{item_id}` to require `user_id` param and validate ownership (return 404 if mismatch)
- [x] 3.3 Save `user_id` on message rows in the chat endpoints and worker
- [x] 3.4 Update `GET /api/chat/{conversation_id}/messages` to require `user_id` param and validate conversation ownership

## 4. Frontend: User Identity Module

- [x] 4.1 Create `frontend/src/lib/user.ts` with `getUserId()` that generates `guest_<uuid>` and persists in localStorage
- [x] 4.2 Replace hardcoded `const USER_ID = 'user_abc'` in `frontend/src/api/index.ts` with `getUserId()` calls
- [x] 4.3 Update `removeFromCart` and `updateCartQuantity` to pass `user_id` in the request (matching new backend API)
- [x] 4.4 Update `loadConversation` to pass `user_id` as a query param

## 5. Testing

- [x] 5.1 Update `backend/tests/test_cart.py` to test ownership validation (delete/update another user's item returns 404)
- [x] 5.2 Update `backend/tests/test_integration.py` to verify user record creation on first request
- [x] 5.3 Verify end-to-end: two browser sessions get independent carts and chat histories (manual — each browser gets unique guest ID via localStorage)
