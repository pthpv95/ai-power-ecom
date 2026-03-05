## Why

The entire application uses a hardcoded `user_abc` string as the user identity. This means every browser session shares the same cart, chat history, and conversation context. Multiple users (or even multiple tabs) cannot have independent shopping experiences. Replacing this with auto-generated guest identities enables proper per-session isolation without the complexity of a full auth system.

## What Changes

- **Frontend**: Replace hardcoded `USER_ID = 'user_abc'` with an auto-generated unique guest ID persisted in `localStorage`
- **Frontend**: Create a user identity module that generates, stores, and retrieves the guest user ID
- **Backend**: Add a `users` table to track guest users with their generated IDs
- **Backend**: Add a user registration/lookup endpoint (`POST /api/users/guest`) that creates or retrieves a guest user
- **Backend**: Add `user_id` column to `messages` table for conversation ownership isolation
- **Backend**: Add ownership validation on cart delete/update and conversation access endpoints

## Capabilities

### New Capabilities
- `guest-identity`: Auto-generated unique user identity per browser session, persisted in localStorage, with backend user record creation and ownership validation on protected resources (cart, conversations)

### Modified Capabilities
_(none — no existing specs to modify)_

## Impact

- **Frontend**: `frontend/src/api/index.ts` — replace constant with dynamic user ID from localStorage
- **Backend models**: `backend/app/models.py` — new `User` model, add `user_id` to `Message`
- **Backend routes**: `backend/app/api/cart.py`, `backend/app/api/chat.py` — ownership checks
- **Database**: New migration for `users` table and `messages.user_id` column
- **Tests**: Update test fixtures to use generated user IDs instead of hardcoded strings
