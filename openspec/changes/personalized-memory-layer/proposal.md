## Why

The shopping assistant currently treats every conversation independently — it has no long-term memory of user preferences. If a user repeatedly asks for "waterproof hiking boots under $150" or always prefers a specific brand, the agent can't learn from that. A persistent memory layer would let the agent automatically extract and recall preferences (brands, sizes, budget ranges, categories, style) per user, making conversations shorter and recommendations more relevant over time.

## What Changes

- Add a `user_memories` table to store extracted preference facts per user (e.g., "prefers Nike", "budget usually under $200", "shoe size 10")
- Add a memory extraction step in the agent loop that analyzes conversations and persists learned preferences
- Inject relevant user memories into the agent's system prompt so it can personalize responses without the user repeating themselves
- Add a new `get_user_preferences` tool so the agent can explicitly query stored memories when needed
- Add a `manage_memory` tool so users can ask the agent to forget or correct stored preferences

## Capabilities

### New Capabilities
- `memory-extraction`: Automatic extraction of user preferences from conversation turns and persistence to the database
- `memory-recall`: Injection of stored user memories into agent context and tool-based preference lookup for personalized recommendations

### Modified Capabilities
_None — this is additive and does not change existing spec-level behavior._

## Impact

- **Database**: New `user_memories` table + Alembic migration
- **Agent graph**: New node or post-processing step for memory extraction; modified system prompt assembly to include memories
- **Agent tools**: Two new tools (`get_user_preferences`, `manage_memory`)
- **Context manager**: Extended to incorporate memory context alongside conversation history within the token budget
- **Models**: New `UserMemory` SQLAlchemy model
- **No frontend changes** — memory is fully backend-driven and transparent to the user through the existing chat interface
