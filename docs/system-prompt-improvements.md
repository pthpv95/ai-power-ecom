# System Prompt Improvements — Lessons Learned

## Date: 2026-02-28

## Bug: LLM Failed to Remove Cart Item

### Symptom
User said "remove the boots" after the agent showed the cart contents. The LLM failed to call `remove_from_cart` because it didn't know the `product_id`.

### Root Cause
Two issues working together:

1. **`get_current_cart` tool didn't include product IDs in its output.** It returned:
   ```
   • TrailMaster Waterproof Hiking Boots x2 — $179.98
   ```
   But the LLM needed:
   ```
   • [ID:7] TrailMaster Waterproof Hiking Boots x2 — $179.98
   ```

2. **System prompt had no rule to check the cart before removing.** The LLM tried to resolve "the boots" to a product ID from memory alone, with no `[ID:X]` tag available.

### Fix
- Added `[ID:{product_id}]` to `get_current_cart` output (`app/agent/tools.py:184`)
- Added "call `get_current_cart` first before removing" rule to the system prompt

### Takeaway
Every tool that mentions products must include the `[ID:X]` tag. The LLM relies on this tag to resolve references like "the boots" or "the first one" into a concrete `product_id`. If any tool omits it, the chain breaks.

---

## Edge Case: Multiple Matching Items

### Scenario
Cart has 3 different boots. User says "remove the boots."

### Problem
`remove_from_cart` takes a single `product_id`. The LLM might guess, remove just one, or call it three times — unpredictable behavior.

### Fix
Added a prompt rule: when multiple items match a removal request, ask the user which one. If they say "all", remove each one individually or use `clear_cart`.

---

## System Prompt Restructure

### Before: Flat list of rules
```
Rules:
- ONLY recommend products returned by search_products...
- ALWAYS include the product ID in brackets...
- Always show product name and price...
- When the user refers to a product...
- When the user wants to add...
- When the user wants to remove...
- If you realize you added the wrong product...
- Be concise and conversational...
- If the user asks something unrelated...
- When comparing products...
```

### Problems with flat lists
1. **No priority** — all rules look equally important, so the LLM treats them that way
2. **No structure** — cart rules, display rules, and style rules are interleaved
3. **Diminishing returns** — more rules = each rule gets less attention (especially with GPT-4o-mini)
4. **Missing happy path** — lots of edge case rules but no guidance on the normal flow
5. **No tool strategy** — doesn't tell the LLM *when* to call tools (e.g., "search first", "check cart before removing")

### After: Sectioned prompt with markdown headers

```
## Core Principle       → the single most important rule (grounding)
## Displaying Products  → the [ID:X] format contract
## Cart Operations      → adding, removing, error correction
## Style                → tone, format, boundaries
```

### Why this works better
| Technique | Effect |
|-----------|--------|
| Markdown headers (`##`) | GPT-4o-mini follows section-based instructions more reliably than flat lists |
| Core principle first | The most critical rule (no hallucinated products) gets the most weight |
| Grouped by concern | Cart rules are together, display rules are together — no interleaving |
| Fewer rules total | Less dilution — each rule gets more attention |
| Positive instructions | "Search first" and "call get_current_cart first" tell the LLM what TO DO, not just what to avoid |

### Key principles for writing system prompts

1. **Structure > length.** A shorter, well-organized prompt outperforms a long flat list.
2. **Put the most important rule first.** LLMs give more weight to earlier instructions.
3. **Group rules by concern.** Don't mix cart logic with display formatting.
4. **Tell the LLM when to use tools.** Tool docstrings describe *what* a tool does; the system prompt should describe *when* to use it.
5. **Positive > negative.** "Search first" is clearer than "don't invent products."
6. **Every tool output must be LLM-friendly.** If the LLM needs a product ID to act, every tool that mentions products must include it.

---

## Files Changed
- `app/agent/tools.py` — Added `[ID:{product_id}]` to `get_current_cart` output (line 184)
- `app/agent/graph.py` — Restructured `SYSTEM_PROMPT` into sections with markdown headers
