## Context

The agent currently uses a sliding window with summarization for conversation context (4K token budget, 6 recent messages kept verbatim). User identity exists via guest IDs stored in localStorage. However, there is no persistent memory of user preferences across conversations. Every new conversation starts from zero — the agent has no knowledge of what the user has previously searched for, preferred brands, budget ranges, or sizing.

The `user_memories` concept is inspired by systems like ChatGPT's memory and Mem0 — the agent observes conversations and automatically extracts preference "facts" that persist across sessions.

## Goals / Non-Goals

**Goals:**
- Automatically extract user preferences from conversations without explicit user action
- Store preferences per user in PostgreSQL for durability
- Inject relevant memories into the agent's context so it can personalize responses
- Allow users to ask the agent to forget or correct stored preferences
- Keep memory extraction lightweight — no extra LLM call on every message

**Non-Goals:**
- Collaborative filtering or recommendation engine (no cross-user learning)
- User authentication or login system
- Frontend UI for managing memories (memory management happens through chat)
- Real-time preference learning within a single turn (extraction happens post-conversation or at natural breakpoints)
- Embedding-based memory retrieval (simple keyword/category matching is sufficient at this scale)

## Decisions

### 1. Memory storage: Structured facts in PostgreSQL (not vector store)

**Decision:** Store memories as structured rows in a `user_memories` table with fields like `category`, `key`, `value`, and `confidence`.

**Rationale:** At this scale (dozens of facts per user, not thousands), structured storage with simple filtering is more predictable and debuggable than vector similarity search. It also avoids adding another Pinecone index. Memories are discrete facts ("prefers Nike", "shoe size 10"), not semantic documents.

**Alternative considered:** Storing memories as embeddings in Pinecone and doing similarity retrieval. Rejected because it adds complexity for a small dataset, and structured facts are easier to update/delete precisely.

### 2. Extraction timing: End of agent response cycle

**Decision:** Run memory extraction as a post-processing step after the agent produces its final response (inside the worker, after the response is streamed). This avoids adding latency to the user-facing response.

**Rationale:** Extracting during the conversation would add latency. Extracting at the end of each agent turn lets us analyze the full exchange context. We use `gpt-4o-mini` (same as the summarizer) to keep costs low.

**Alternative considered:** Batch extraction via a scheduled job. Rejected because it delays personalization — the user wouldn't benefit until the next scheduled run.

### 3. Memory injection: Prepend to system prompt

**Decision:** Load the user's memories from the DB and append them to the system prompt as a structured block (e.g., "Known user preferences: ...") before invoking the agent.

**Rationale:** This is the simplest integration point. The agent already receives a system prompt; adding a preferences section requires no graph changes. Token cost is minimal (typically <200 tokens for a reasonable set of preferences).

**Alternative considered:** A dedicated `recall_memories` tool the agent calls on every turn. Rejected because it adds a mandatory tool call round-trip to every conversation, increasing latency. Instead, memories are always available in context, and the agent has an optional `get_user_preferences` tool for explicit queries.

### 4. Memory schema: Category + key-value with confidence

**Decision:** Each memory is a row with: `user_id`, `category` (enum: brand, size, budget, category, style, other), `key` (the preference name), `value` (the preference detail), `confidence` (float 0-1), `source_message_id`, timestamps.

**Rationale:** Categories enable efficient filtering and structured injection ("Your size preferences: ..., Your brand preferences: ..."). Confidence lets us weight memories — a preference mentioned once is weaker than one mentioned repeatedly. `source_message_id` provides traceability.

### 5. Deduplication and update strategy: Upsert by (user_id, category, key)

**Decision:** When extracting a memory that matches an existing (user_id, category, key), update the value and increase confidence rather than creating a duplicate.

**Rationale:** Users may refine preferences ("actually, size 11 not 10"). Upsert ensures the latest preference wins while boosting confidence for consistently repeated ones.

## Risks / Trade-offs

- **Incorrect extraction** → The LLM might extract wrong preferences. Mitigation: confidence scoring (low confidence for single mentions), and the `manage_memory` tool lets users correct mistakes.
- **Privacy sensitivity** → Storing user preferences raises privacy concerns. Mitigation: memories are scoped to guest IDs (no PII), users can delete memories via chat, and we document data retention.
- **Token budget pressure** → Adding memories to the system prompt reduces the budget for conversation history. Mitigation: cap memories at ~500 tokens, prioritize high-confidence memories, and adjust the context manager's budget allocation.
- **Extraction cost** → Extra LLM call per agent turn. Mitigation: use `gpt-4o-mini` (cheap), skip extraction if the conversation had no product-related discussion.
