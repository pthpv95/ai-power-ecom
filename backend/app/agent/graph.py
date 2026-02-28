"""
LangGraph agent — the core reasoning loop.
"""
from typing import Annotated

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.config import settings
from app.agent.tools import ALL_TOOLS


# ── State ─────────────────────────────────────────────────────────────────────
# Only serializable data goes here. db and user_id live in contextvars.
# Annotated[list, add_messages] tells LangGraph to append, not replace.

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ── LLM ───────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a concise, helpful outdoor gear shopping assistant.

## Core Principle
You can ONLY discuss products returned by search_products. Never invent or assume products exist. When in doubt, search first.

## Displaying Products
- Format: [ID:7] UltraLight 20F Sleeping Bag — $149.99
- The [ID:X] tag is critical — always include it. It's how you track products across turns.
- When the user refers to "the first one" or "the cheaper one", look up the [ID:X] tag in your earlier messages to resolve the correct product.

## Cart Operations
- Adding: If only one product matches, add it directly. If ambiguous, ask which one.
- Removing: Call get_current_cart first to see what's there. If multiple items match "remove the boots", ask which one. If the user says "all", remove each one.
- Wrong item added: Immediately remove_from_cart the wrong item, add_to_cart the right one, and briefly apologize.

## Style
- Be concise. Use bullet points for product lists.
- When comparing, highlight price, weight, and key feature differences.
- Redirect off-topic questions politely.
"""

OPENAI_MODEL = "gpt-4o-mini"

llm = ChatOpenAI(
    model=OPENAI_MODEL,
    api_key=settings.openai_api_key,
    temperature=0,
)

llm_with_tools = llm.bind_tools(ALL_TOOLS)


# ── Node 1: agent_node ───────────────────────────────────────────────────────

async def agent_node(state: AgentState) -> dict:
    messages = state["messages"]

    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


# ── Node 2: tool_node ────────────────────────────────────────────────────────
# Much simpler now — db and user_id come from contextvars,
# so we just call the tool with the args GPT-4o provided.

TOOL_MAP = {t.name: t for t in ALL_TOOLS}

async def tool_node(state: AgentState) -> dict:
    last_message: AIMessage = state["messages"][-1]

    results = []
    for tool_call in last_message.tool_calls:
        tool_fn = TOOL_MAP[tool_call["name"]]
        result = await tool_fn.ainvoke(tool_call["args"])

        results.append(
            ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"],
                name=tool_call["name"],
            )
        )

    return {"messages": results}


# ── Conditional Edge ──────────────────────────────────────────────────────────

def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"


# ── Build the Graph ───────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "agent")

    return graph.compile()


agent = build_graph()
