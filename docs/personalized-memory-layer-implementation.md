# Personalized Memory Layer Implementation

This document describes the backend changes made for the `personalized-memory-layer` OpenSpec change.

## Goal

Add persistent user preference memory so the shopping assistant can:

- extract preferences from completed conversations
- store those preferences durably in PostgreSQL
- inject relevant preferences into the system prompt on later turns
- let the agent inspect, update, or delete stored preferences through tools

## Files Changed

### Persistence

- `backend/app/models.py`
- `backend/alembic/versions/b6f8a1c2d3e4_add_user_memories_table.py`

### Services

- `backend/app/services/memory_extractor.py`
- `backend/app/services/memory_recall.py`
- `backend/app/services/context_manager.py`

### Agent Runtime

- `backend/app/agent/graph.py`
- `backend/app/agent/tools.py`
- `backend/app/api/chat.py`
- `backend/app/worker.py`

### Tests

- `backend/tests/test_memory_extractor.py`
- `backend/tests/test_memory_recall.py`
- `backend/tests/test_memory_tools.py`
- `backend/tests/test_memory_integration.py`

### OpenSpec Tracking

- `openspec/changes/personalized-memory-layer/tasks.md`

## Data Model

### `MemoryCategory`

Added a string enum with these values:

- `brand`
- `size`
- `budget`
- `category`
- `style`
- `other`

### `UserMemory`

Added a new SQLAlchemy model and migration for `user_memories` with:

- `id`
- `user_id`
- `category`
- `key`
- `value`
- `confidence`
- `source_message_id`
- `created_at`
- `updated_at`

Constraints and indexing:

- unique constraint on `(user_id, category, key)`
- index on `user_id`
- foreign key from `source_message_id` to `messages.id`

## Memory Extraction

Implemented in `backend/app/services/memory_extractor.py`.

### What it does

- inspects conversation messages for product-related signals
- skips extraction when the conversation is not about products or preferences
- calls `gpt-4o-mini` to extract stable preference facts as JSON
- parses and normalizes extracted facts into structured memory rows
- upserts by `(user_id, category, key)`

### Skip Logic

Extraction is bypassed unless the conversation contains:

- product-related keywords such as `jackets`, `boots`, `price`, `budget`, `size`, `cart`
- or tool activity, such as prior product-search tool calls

This keeps extraction off generic greetings and non-shopping turns.

### Upsert Rules

- first insert starts at confidence `0.5`
- repeated extraction for the same `(user_id, category, key)` bumps confidence by `0.1`
- confidence is capped at `1.0`
- latest extracted `value` replaces the old value
- `source_message_id` is refreshed on update

## Memory Recall

Implemented in `backend/app/services/memory_recall.py`.

### What it does

- loads memories for a user from PostgreSQL
- orders memories by confidence descending, then most recently updated
- caps the injected block to approximately `500` tokens
- formats memories into a stable prompt block

### Prompt Block Format

When memories exist, the block looks like:

```text
Known user preferences:
- brand:
  - jackets: Patagonia (confidence 0.90)
- budget:
  - boots: under $150 (confidence 0.70)
```

If the user has no memories, no preference block is added.

## System Prompt Integration

The memory layer is currently used in the system prompt path.

### `backend/app/agent/graph.py`

Added:

- `compose_system_prompt(memory_block)`
- `build_system_prompt_with_memories()`

`agent_node()` now prepends a `SystemMessage` that includes the base system prompt plus the user’s recalled memories.

### `backend/app/worker.py`

The streaming worker also loads the same memory block and prepends it before model invocation.

This keeps the streaming path and the non-streaming `/api/chat` path aligned.

## Token Budget Changes

The existing conversation-history budget is still `4000` tokens, but part of that budget is now reserved for the memory block.

### `backend/app/services/context_manager.py`

Added `build_context_with_reserved_tokens(...)`.

This lets callers reduce the effective history budget by the number of tokens consumed by the recalled memory block.

### Call Sites Updated

- `backend/app/api/chat.py`
- `backend/app/worker.py`

Both paths now:

1. load the user memory block
2. count its tokens
3. reserve that amount from history before building conversation context

## Agent Tools

Implemented in `backend/app/agent/tools.py`.

### `get_user_preferences`

Reads stored memories for the current `user_id`.

Behavior:

- optional category filter
- returns formatted preferences grouped by category
- returns a helpful message when no preferences exist
- validates category values

### `manage_memory`

Supports:

- `delete` by `category + key`
- `update` by `category + key + value`

Behavior:

- validates category
- returns a clear message if no matching memory exists
- commits changes immediately

Both tools were registered in `ALL_TOOLS`, which means they are available to the agent.

## Worker Post-Processing

Implemented in `backend/app/worker.py`.

After the assistant response is fully generated and saved:

- the worker assembles the conversation messages used during the run
- appends the final assistant response
- passes that material into the memory extraction service
- stores extracted memories for the current user

Error handling:

- extraction failures are caught
- errors are logged with `logger.exception(...)`
- the user response is not affected

This preserves the requirement that extraction happens asynchronously after the user-visible response completes.

## Tests Added

### `backend/tests/test_memory_extractor.py`

Covers:

- JSON parsing from fenced code blocks
- category normalization
- skip logic for non-product conversations
- extraction trigger behavior
- LLM-output parsing path

### `backend/tests/test_memory_recall.py`

Covers:

- confidence ordering
- token capping
- empty-memory behavior

### `backend/tests/test_memory_tools.py`

Covers:

- reading stored preferences
- updating a stored memory
- deleting a stored memory

### `backend/tests/test_memory_integration.py`

Covers:

- extraction from a conversation
- persistence into `user_memories`
- later prompt injection through `build_system_prompt_with_memories()`

## Verification Performed

The following verification succeeded:

```bash
cd backend
env UV_CACHE_DIR=/tmp/uv-cache uv run python -m compileall app tests
env UV_CACHE_DIR=/tmp/uv-cache uv run pytest --noconftest tests/test_memory_extractor.py -k 'parse_extracted_memories_handles_json_code_fence or normalize_memory_category_maps_aliases or should_extract_memories_skips_non_product_chat or should_extract_memories_detects_tool_signals or extract_preference_facts_uses_llm_output'
```

## Verification Limits Encountered

Full database-backed verification was not completed in this Codex session because:

- sandboxed runs could not open a socket to local PostgreSQL
- full app import during pytest also depends on Pinecone availability

Commands intended for local follow-up:

```bash
cd backend
uv run alembic upgrade head
UV_CACHE_DIR=/tmp/uv-cache uv run pytest
```

## Current Behavior Summary

As implemented now:

- personalized memory is persisted in the database
- personalized memory is used in system prompt assembly
- the context window reserves space for the recalled memory block
- the agent can read, update, and delete stored preferences
- extraction runs after the assistant response and does not block the user-facing output

## Commit Scope

This change is backend-only. No frontend files were modified.
