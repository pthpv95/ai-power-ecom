## ADDED Requirements

### Requirement: Guest user ID generation
The frontend SHALL generate a unique guest user ID in the format `guest_<uuid-v4>` on first visit and persist it in `localStorage` under the key `guest_user_id`.

#### Scenario: First visit generates new ID
- **WHEN** a user visits the app for the first time (no `guest_user_id` in localStorage)
- **THEN** the system generates a `guest_<uuid-v4>` string and stores it in localStorage

#### Scenario: Subsequent visits reuse existing ID
- **WHEN** a user revisits the app (localStorage contains `guest_user_id`)
- **THEN** the system uses the stored ID without generating a new one

#### Scenario: All API calls use the guest ID
- **WHEN** any API call requires a `user_id` parameter
- **THEN** the system uses the guest ID from localStorage instead of a hardcoded value

### Requirement: Backend user record creation
The backend SHALL create a `users` table with columns: `id` (string, primary key), `created_at` (timestamp). A user record SHALL be created lazily when the user's first cart or chat request is processed.

#### Scenario: First request creates user record
- **WHEN** an API request is received with a `user_id` that does not exist in the `users` table
- **THEN** the system creates a new row in `users` with that ID and current timestamp

#### Scenario: Subsequent requests reuse existing user
- **WHEN** an API request is received with a `user_id` that already exists in the `users` table
- **THEN** no new user record is created

### Requirement: Cart ownership validation
The backend SHALL validate that cart mutation operations (delete, update quantity) belong to the requesting user.

#### Scenario: Delete own cart item succeeds
- **WHEN** a user sends DELETE for a cart item they own
- **THEN** the item is removed and a 200 response is returned

#### Scenario: Delete another user's cart item fails
- **WHEN** a user sends DELETE for a cart item owned by a different user
- **THEN** the system returns 404 (not found) without deleting the item

#### Scenario: Update own cart item quantity succeeds
- **WHEN** a user sends PATCH to update quantity on their own cart item
- **THEN** the quantity is updated and a 200 response is returned

#### Scenario: Update another user's cart item fails
- **WHEN** a user sends PATCH to update quantity on another user's cart item
- **THEN** the system returns 404 without modifying the item

### Requirement: Conversation ownership
The backend SHALL associate conversations with a user_id and validate ownership on access.

#### Scenario: Messages are stored with user_id
- **WHEN** a chat message is saved to the database
- **THEN** the message row includes the `user_id` of the requesting user

#### Scenario: Loading conversation checks ownership
- **WHEN** a user requests messages for a conversation_id
- **THEN** the system returns messages only if the conversation belongs to that user

#### Scenario: Accessing another user's conversation fails
- **WHEN** a user requests messages for a conversation they do not own
- **THEN** the system returns 404 (not found)

### Requirement: Frontend user identity module
The frontend SHALL provide a centralized `getUserId()` function that all API calls use to obtain the current user ID.

#### Scenario: API module uses getUserId
- **WHEN** the API module is initialized
- **THEN** all functions that require user_id call `getUserId()` instead of referencing a hardcoded constant

#### Scenario: Replacing hardcoded USER_ID
- **WHEN** the change is complete
- **THEN** the `const USER_ID = 'user_abc'` line no longer exists in the codebase
