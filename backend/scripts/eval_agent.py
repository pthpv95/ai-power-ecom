"""
LangSmith eval for agent tool selection.

Tests whether the LLM picks the correct tool for a given user message.

Includes:
1. Single-turn: user message → expected first tool (no DB needed)
2. End-to-end multi-turn: runs the FULL agent graph with real DB + Pinecone
   across multiple conversation turns, then checks if the agent called the
   right tool with the right args.

Usage:
    cd backend
    uv run python scripts/eval_agent.py              # run all evals
    uv run python scripts/eval_agent.py single       # single-turn only
    uv run python scripts/eval_agent.py multi        # multi-turn only
"""

import asyncio
import os
import re
import sys

from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langsmith import Client, evaluate

# Import the LLM + tools binding and system prompt from the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.agent.graph import SYSTEM_PROMPT, agent, llm_with_tools
from app.agent.context import db_var, user_id_var
from app.database import SessionLocal

# ── Config ───────────────────────────────────────────────────────────────────

DATASET_NAME = "agent-tool-selection"

EVAL_USER_ID = "eval-user-00"

# Single-turn examples: just a user message → expected first tool
EXAMPLES = [
    {"input": "Show me rain jackets", "expected_tool": "search_products"},
    {"input": "Find sleeping bags under $100", "expected_tool": "search_products"},
    {"input": "What's in my cart?", "expected_tool": "get_current_cart"},
    {"input": "Add product 5 to my cart", "expected_tool": "add_to_cart"},
    {"input": "Remove product 3 from my cart", "expected_tool": "remove_from_cart"},
    {"input": "Tell me more about product 12", "expected_tool": "get_product_details"},
    {"input": "Compare product 3 and product 7", "expected_tool": "compare_products"},
    {"input": "What's the weather today?", "expected_tool": None},
]

# End-to-end multi-turn examples.
# Each turn is a user message. The agent runs the full graph (search, tool execution, etc.)
# for each turn. After all turns, we check the final turn's tool calls.
#
# "expected_tool" is checked against the LAST turn's tool calls.
# "expected_behavior" describes what correct behavior looks like — used for the
# LLM-as-judge evaluator since we can't hardcode product IDs (they come from live search).
E2E_MULTI_TURN_EXAMPLES = [
    {
        "description": "Compare hydration products, then add the cheaper one",
        "turns": [
            "compare hydration products",
            "add the cheaper one to my cart",
        ],
        "expected_tool": "add_to_cart",
        "expected_behavior": (
            "The agent should call add_to_cart with the product_id of whichever "
            "hydration product had the lower price in the comparison from turn 1. "
            "It must NOT ask the user to clarify — it should resolve 'the cheaper one' "
            "from the prior context."
        ),
    },
]

E2E_DATASET_NAME = "agent-e2e-multi-turn"


# ── Dataset creation (idempotent) ────────────────────────────────────────────

def get_or_create_dataset(client: Client, name: str, examples: list[dict], *, build_inputs_outputs=None) -> str:
    """Return the dataset ID. Create it if it doesn't exist."""
    for ds in client.list_datasets(dataset_name=name):
        print(f"Dataset '{name}' already exists (id={ds.id})")
        return ds.id

    dataset = client.create_dataset(
        dataset_name=name,
        description=f"Agent eval: {name}",
    )

    for ex in examples:
        if build_inputs_outputs:
            inputs, outputs = build_inputs_outputs(ex)
        else:
            inputs = {"input": ex["input"]}
            outputs = {"expected_tool": ex["expected_tool"]}

        client.create_example(
            dataset_id=dataset.id,
            inputs=inputs,
            outputs=outputs,
        )

    print(f"Created dataset '{name}' with {len(examples)} examples")
    return dataset.id


# ── Target function: single-turn ─────────────────────────────────────────────

def predict(inputs: dict) -> dict:
    """Single-turn: call the LLM with tools and return the response."""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=inputs["input"]),
    ]
    response = llm_with_tools.invoke(messages)

    tool_calls = response.tool_calls if response.tool_calls else []
    first_tool = tool_calls[0]["name"] if tool_calls else None

    return {
        "first_tool": first_tool,
        "all_tools": [tc["name"] for tc in tool_calls],
        "response": response.content,
    }


# ── Target function: e2e multi-turn (real agent graph) ──────────────────────

async def _run_e2e_conversation(turns: list[str]) -> dict:
    """Run a multi-turn conversation through the real agent graph.

    Sets up a real DB session and contextvars, then sends each turn
    through agent.ainvoke(), accumulating messages across turns.

    Returns all messages, plus details about the last turn's tool calls.
    """
    async with SessionLocal() as db:
        db_var.set(db)
        user_id_var.set(EVAL_USER_ID)

        # Accumulate messages across turns (the agent's "memory")
        all_messages = []
        last_turn_tool_calls = []

        for i, user_msg in enumerate(turns):
            all_messages.append(HumanMessage(content=user_msg))

            # Run the full agent graph — it will call tools, loop, etc.
            result = await agent.ainvoke({"messages": all_messages})

            # Extract new messages added by this turn
            new_messages = result["messages"][len(all_messages):]
            all_messages = result["messages"]

            # Track tool calls from this turn's AI messages
            if i == len(turns) - 1:
                # Last turn — capture tool calls for evaluation
                for msg in new_messages:
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        last_turn_tool_calls.extend(msg.tool_calls)

        # Build a readable transcript for the LLM-as-judge
        transcript_lines = []
        for msg in all_messages:
            if isinstance(msg, SystemMessage):
                continue
            elif isinstance(msg, HumanMessage):
                transcript_lines.append(f"USER: {msg.content}")
            elif isinstance(msg, AIMessage):
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        transcript_lines.append(
                            f"AGENT TOOL CALL: {tc['name']}({tc['args']})"
                        )
                if msg.content:
                    transcript_lines.append(f"AGENT: {msg.content}")
            elif isinstance(msg, ToolMessage):
                # Truncate long tool results
                content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                transcript_lines.append(f"TOOL RESULT ({msg.name}): {content}")

        transcript = "\n".join(transcript_lines)

        first_tool = last_turn_tool_calls[0]["name"] if last_turn_tool_calls else None
        first_args = last_turn_tool_calls[0]["args"] if last_turn_tool_calls else None

        return {
            "first_tool": first_tool,
            "first_args": first_args,
            "all_tools": [tc["name"] for tc in last_turn_tool_calls],
            "transcript": transcript,
        }


def predict_e2e(inputs: dict) -> dict:
    """End-to-end multi-turn prediction (sync wrapper for LangSmith evaluate)."""
    turns = inputs["turns"]
    return asyncio.run(_run_e2e_conversation(turns))


# ── Evaluators ───────────────────────────────────────────────────────────────

def correct_tool(outputs: dict, reference_outputs: dict) -> dict:
    """Score 1 if the first tool called matches the expected tool."""
    expected = reference_outputs.get("expected_tool")
    actual = outputs.get("first_tool")
    return {"key": "correct_tool", "score": int(actual == expected)}


def tool_called(outputs: dict, reference_outputs: dict) -> dict:
    """Score 1 if tool usage matches expectation (called for on-topic, not called for off-topic)."""
    expected = reference_outputs.get("expected_tool")
    actual = outputs.get("first_tool")

    if expected is None:
        score = int(actual is None)
    else:
        score = int(actual is not None)

    return {"key": "tool_called", "score": score}


def correct_product_picked(outputs: dict, reference_outputs: dict) -> dict:
    """Score 1 if the agent picked the cheaper product from the conversation.

    Parses the transcript to find product prices from the first turn,
    determines which was cheaper, and checks if add_to_cart was called
    with that product's ID.
    """
    transcript = outputs.get("transcript", "")
    first_args = outputs.get("first_args")
    first_tool = outputs.get("first_tool")

    if first_tool != "add_to_cart" or not first_args:
        return {"key": "correct_product_picked", "score": 0}

    added_product_id = first_args.get("product_id")

    # Parse all [ID:X] ... $price patterns from the transcript
    # This captures product info from tool results and agent messages
    product_prices = {}
    for match in re.finditer(r"\[ID:(\d+)\].*?\$(\d+(?:\.\d+)?)", transcript):
        pid = int(match.group(1))
        price = float(match.group(2))
        if pid not in product_prices:
            product_prices[pid] = price

    if len(product_prices) < 2:
        # Can't determine which is cheaper if we don't have 2+ products
        return {"key": "correct_product_picked", "score": 0}

    cheapest_id = min(product_prices, key=product_prices.get)

    score = int(added_product_id == cheapest_id)
    return {"key": "correct_product_picked", "score": score}


# ── Main ─────────────────────────────────────────────────────────────────────

def run_single_turn(client: Client):
    """Run single-turn tool selection eval."""
    get_or_create_dataset(client, DATASET_NAME, EXAMPLES)

    print("\nRunning single-turn evaluation...")
    results = evaluate(
        predict,
        data=DATASET_NAME,
        evaluators=[correct_tool, tool_called],
        experiment_prefix="tool-selection",
    )

    print("\n" + "=" * 60)
    print("SINGLE-TURN RESULTS")
    print("=" * 60)

    correct_count = 0
    total = 0
    for result in results:
        total += 1
        user_input = result["run"].inputs["input"]
        expected = result["example"].outputs["expected_tool"]
        actual = result["run"].outputs.get("first_tool")
        is_correct = actual == expected
        if is_correct:
            correct_count += 1
        status = "PASS" if is_correct else "FAIL"
        print(f"  [{status}] \"{user_input}\"")
        print(f"         expected={expected}, got={actual}")

    print(f"\nScore: {correct_count}/{total} correct")
    return results


def run_e2e_multi_turn(client: Client):
    """Run end-to-end multi-turn eval with real agent graph."""

    def build_e2e_inputs_outputs(ex):
        inputs = {"turns": ex["turns"]}
        outputs = {
            "expected_tool": ex["expected_tool"],
            "expected_behavior": ex["expected_behavior"],
        }
        return inputs, outputs

    get_or_create_dataset(
        client, E2E_DATASET_NAME, E2E_MULTI_TURN_EXAMPLES,
        build_inputs_outputs=build_e2e_inputs_outputs,
    )

    print("\nRunning end-to-end multi-turn evaluation...")
    print("(This runs the full agent graph with real DB + Pinecone)\n")

    mt_results = evaluate(
        predict_e2e,
        data=E2E_DATASET_NAME,
        evaluators=[correct_tool, correct_product_picked],
        experiment_prefix="e2e-multi-turn",
    )

    print("\n" + "=" * 60)
    print("E2E MULTI-TURN RESULTS")
    print("=" * 60)

    for result in mt_results:
        user_turns = result["run"].inputs["turns"]
        expected_tool = result["example"].outputs["expected_tool"]
        actual_tool = result["run"].outputs.get("first_tool")
        actual_args = result["run"].outputs.get("first_args")
        transcript = result["run"].outputs.get("transcript", "")

        tool_ok = actual_tool == expected_tool

        status = "PASS" if tool_ok else "FAIL"
        print(f"\n  [{status}] Multi-turn conversation:")
        for i, turn in enumerate(user_turns, 1):
            print(f"         Turn {i}: \"{turn}\"")
        print(f"         expected tool={expected_tool}, got={actual_tool}")
        print(f"         args={actual_args}")

        # Print condensed transcript
        print(f"\n  Transcript:")
        for line in transcript.split("\n"):
            print(f"    | {line}")

    return mt_results


def main():
    client = Client()

    # Parse CLI arg to select which eval to run
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    all_results = []

    if mode in ("all", "single"):
        all_results.append(run_single_turn(client))

    if mode in ("all", "multi"):
        all_results.append(run_e2e_multi_turn(client))

    # Dashboard links
    names = [r.experiment_name for r in all_results]
    print(f"\nExperiments: {', '.join(names)}")
    print(f"Dashboard:  https://smith.langchain.com/")
    print("  -> Navigate to Datasets to see results")


if __name__ == "__main__":
    main()
