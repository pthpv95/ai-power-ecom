"""
LangSmith eval for agent tool selection.

Tests whether the LLM picks the correct tool for a given user message.
Calls llm_with_tools directly (no DB, no Pinecone needed).

Usage:
    cd backend
    uv run python scripts/eval_agent.py
"""

import os
import sys

from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import Client, evaluate

# Import the LLM + tools binding and system prompt from the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.agent.graph import SYSTEM_PROMPT, llm_with_tools

# ── Config ───────────────────────────────────────────────────────────────────

DATASET_NAME = "agent-tool-selection"

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


# ── Dataset creation (idempotent) ────────────────────────────────────────────

def get_or_create_dataset(client: Client) -> str:
    """Return the dataset ID. Create it if it doesn't exist."""
    for ds in client.list_datasets(dataset_name=DATASET_NAME):
        print(f"Dataset '{DATASET_NAME}' already exists (id={ds.id})")
        return ds.id

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Test cases for agent tool selection evaluation",
    )
    for ex in EXAMPLES:
        client.create_example(
            dataset_id=dataset.id,
            inputs={"input": ex["input"]},
            outputs={"expected_tool": ex["expected_tool"]},
        )
    print(f"Created dataset '{DATASET_NAME}' with {len(EXAMPLES)} examples")
    return dataset.id


# ── Target function ──────────────────────────────────────────────────────────

def predict(inputs: dict) -> dict:
    """Call the LLM with tools and return the response."""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=inputs["input"]),
    ]
    response = llm_with_tools.invoke(messages)

    # Extract tool call info
    tool_calls = response.tool_calls if response.tool_calls else []
    first_tool = tool_calls[0]["name"] if tool_calls else None

    return {
        "first_tool": first_tool,
        "all_tools": [tc["name"] for tc in tool_calls],
        "response": response.content,
    }


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
        # Off-topic: should NOT call any tool
        score = int(actual is None)
    else:
        # On-topic: should call some tool
        score = int(actual is not None)

    return {"key": "tool_called", "score": score}


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    client = Client()
    dataset_id = get_or_create_dataset(client)

    print("\nRunning evaluation...")
    results = evaluate(
        predict,
        data=DATASET_NAME,
        evaluators=[correct_tool, tool_called],
        experiment_prefix="tool-selection",
    )

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS")
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

    # Print link to LangSmith dashboard
    experiment_name = results.experiment_name
    print(f"\nExperiment: {experiment_name}")
    print(f"Dashboard:  https://smith.langchain.com/")
    print("  -> Navigate to Datasets > agent-tool-selection to see results")


if __name__ == "__main__":
    main()
