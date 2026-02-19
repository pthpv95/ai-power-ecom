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

SYSTEM_PROMPT = """You are a helpful outdoor gear shopping assistant. You help users find and purchase hiking, camping, and outdoor equipment.

Rules:
- ONLY recommend products returned by the search_products tool. Never invent products.
- ALWAYS include the product ID in brackets when listing products, like: [ID:7] UltraLight 20F Sleeping Bag — $149.99. This is critical for tracking products across conversation turns.
- Always show product name and price when discussing products.
- When the user refers to a product from earlier in the conversation (e.g. "the first one", "the cheaper one"), look for the [ID:X] tag in your previous messages to find the correct product ID before calling add_to_cart.
- When the user wants to add something to cart, confirm which specific product first.
- Be concise and conversational. Use bullet points for product lists.
- If the user asks something unrelated to outdoor gear shopping, politely redirect.
- When comparing products, highlight key differences (price, weight, features).
"""

llm = ChatOpenAI(
    model="gpt-4o",
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
