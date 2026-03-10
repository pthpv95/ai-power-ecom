## 1. Database & Model

- [x] 1.1 Create `UserMemory` SQLAlchemy model with fields: id, user_id, category (enum: brand/size/budget/category/style/other), key, value, confidence (float, default 0.5), source_message_id (nullable), created_at, updated_at
- [x] 1.2 Generate Alembic migration for `user_memories` table with unique constraint on (user_id, category, key)

## 2. Memory Extraction Service

- [x] 2.1 Create `app/services/memory_extractor.py` with a function that takes conversation messages and uses `gpt-4o-mini` to extract preference facts as structured JSON (category, key, value)
- [x] 2.2 Implement upsert logic: insert new memories with confidence=0.5, update existing ones by bumping confidence and updating value
- [x] 2.3 Add skip logic to bypass extraction when conversation has no product-related content (check for tool calls or product keywords)

## 3. Memory Recall & Context Injection

- [x] 3.1 Create `app/services/memory_recall.py` with a function that loads a user's memories from the DB, ordered by confidence desc, capped at ~500 tokens
- [x] 3.2 Modify the system prompt assembly in `app/agent/graph.py` to append a "Known user preferences" section with loaded memories before invoking the agent
- [x] 3.3 Update the context manager's token budget to account for the memory block (reserve space within the existing budget)

## 4. Agent Tools

- [x] 4.1 Implement `get_user_preferences` tool in `app/agent/tools.py` that queries `user_memories` by user_id with optional category filter, returns formatted preference list
- [x] 4.2 Implement `manage_memory` tool in `app/agent/tools.py` with actions: delete (by category+key) and update (by category+key with new value)
- [x] 4.3 Register both new tools in the agent's tool list in `graph.py`

## 5. Integration with Worker

- [x] 5.1 Add memory extraction call in `app/worker.py` as a post-processing step after the agent response is complete and streamed
- [x] 5.2 Ensure extraction errors are caught and logged without affecting the user response

## 6. Testing

- [x] 6.1 Write unit tests for memory extraction (correct JSON parsing, preference categorization, skip logic)
- [x] 6.2 Write unit tests for memory recall (token capping, confidence ordering, empty memories)
- [x] 6.3 Write integration test: full flow from conversation → extraction → next conversation with injected memories
- [x] 6.4 Test manage_memory tool (delete and update operations)
