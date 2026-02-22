# LangSmith Eval: Agent Tool Selection

## What was built

A standalone eval script (`backend/scripts/eval_agent.py`) that programmatically tests whether the LLM picks the correct tool for a given user message.

### Why LLM-only (not full agent)?
The full agent graph calls tools that need a live DB + Pinecone. For evaluating **tool selection**, we only need the LLM's decision — did it choose `search_products` vs `add_to_cart`? That decision happens in `llm_with_tools.invoke()`, before any tool executes. No infrastructure needed.

## Architecture

```
eval script
  ├── Creates dataset in LangSmith (idempotent — skips if exists)
  ├── Calls llm_with_tools.invoke() for each test case
  ├── Scores with 2 heuristic evaluators
  └── Prints results + LangSmith dashboard link
```

## Test cases (dataset: `agent-tool-selection`)

| Input | Expected Tool |
|-------|--------------|
| "Show me rain jackets" | search_products |
| "Find sleeping bags under $100" | search_products |
| "What's in my cart?" | get_current_cart |
| "Add product 5 to my cart" | add_to_cart |
| "Remove product 3 from my cart" | remove_from_cart |
| "Tell me more about product 12" | get_product_details |
| "Compare product 3 and product 7" | compare_products |
| "What's the weather today?" | None (off-topic) |

## Evaluators

1. **`correct_tool`** — score 1 if first tool called matches expected, 0 otherwise
2. **`tool_called`** — score 1 if any tool was called (on-topic), or no tool was called (off-topic)

## How to run

```bash
cd backend
uv run python scripts/eval_agent.py
```

## First run results (2026-02-22)

Score: **6/8 correct**

Notable failures:
- **"Compare product 3 and product 7"** → LLM responded with text instead of calling `compare_products`. May need a stronger tool description.
- **"Add product 5 to my cart"** → LLM called `get_current_cart` first instead of `add_to_cart`. This is the system prompt's "always confirm which product first" instruction causing the LLM to be cautious.

## Key decisions

- **Custom evaluators over openevals/agentevals** — simple heuristics are sufficient for tool selection; no need for LLM-as-judge overhead
- **`langsmith.evaluate()` API** — handles dataset iteration, run tracking, and experiment dashboard automatically
- **Idempotent dataset creation** — checks for existing dataset before creating, safe to re-run

## Files

| File | Purpose |
|------|---------|
| `backend/scripts/eval_agent.py` | Eval script |
