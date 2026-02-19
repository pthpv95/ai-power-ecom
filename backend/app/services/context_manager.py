"""
Context window management — sliding window with summarization.

The problem: conversations get long. Sending everything to GPT-4o is:
  - Expensive (you pay per token)
  - Slow (more tokens = more latency)
  - Noisy (model loses focus with too much context)

The solution: keep recent messages verbatim, summarize older ones.

┌──────────────────────────────────────────────────┐
│  [Summary of messages 1-15]    (~200 tokens)     │ ← compressed
│  Message 16: user: "..."       (verbatim)        │
│  Message 17: assistant: "..."  (verbatim)        │ ← recent, kept as-is
│  Message 18: user: "..."       (verbatim)        │
│  Message 19: assistant: "..."  (verbatim)        │
│  Message 20: user: "new msg"   (verbatim)        │
└──────────────────────────────────────────────────┘
"""
import tiktoken
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.models import Message

# tiktoken encoder for GPT-4o — used to count tokens accurately
# This is the same tokenizer GPT-4o uses internally
ENCODER = tiktoken.encoding_for_model("gpt-4o")

# Budget: how many tokens we allow for conversation history
# The rest of the context window is reserved for system prompt,
# tool definitions, and the model's response
MAX_HISTORY_TOKENS = 4000

# How many recent messages to always keep verbatim
# (even if they exceed the token budget slightly)
MIN_RECENT_MESSAGES = 6

# LLM for summarization — use a cheaper/faster call
summarizer = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=settings.openai_api_key,
    temperature=0,
)


def count_tokens(text: str) -> int:
    """Count tokens in a string using GPT-4o's tokenizer."""
    return len(ENCODER.encode(text))


def messages_to_langchain(db_messages: list[Message]) -> list[HumanMessage | AIMessage]:
    """Convert DB messages to LangChain message objects."""
    result = []
    for msg in db_messages:
        if msg.role == "user":
            result.append(HumanMessage(content=msg.content))
        else:
            result.append(AIMessage(content=msg.content))
    return result


async def build_context(db_messages: list[Message]) -> list:
    """
    Build the conversation context for the agent.

    Strategy:
      1. Count total tokens in all messages
      2. If under budget → return everything verbatim
      3. If over budget → summarize older messages, keep recent ones verbatim

    Returns a list of LangChain messages ready for the agent.
    """
    if not db_messages:
        return []

    lc_messages = messages_to_langchain(db_messages)

    # Count total tokens
    total_tokens = sum(count_tokens(m.content) for m in lc_messages)

    # Under budget — return everything as-is
    if total_tokens <= MAX_HISTORY_TOKENS:
        return lc_messages

    # Over budget — split into old (to summarize) and recent (to keep)
    recent = lc_messages[-MIN_RECENT_MESSAGES:]
    old = lc_messages[:-MIN_RECENT_MESSAGES]

    if not old:
        # Not enough messages to summarize, just return recent
        return recent

    # Summarize older messages
    summary = await summarize_messages(old)

    # Return: [summary] + recent messages
    return [SystemMessage(content=f"Summary of earlier conversation:\n{summary}")] + recent


async def summarize_messages(messages: list) -> str:
    """
    Compress a list of messages into a short summary.

    We use gpt-4o-mini for this — it's 15x cheaper than gpt-4o
    and fast enough for summarization. The summary captures:
    - What products the user was looking at
    - What's in their cart
    - Key preferences they mentioned
    """
    conversation_text = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in messages
    )

    response = await summarizer.ainvoke([
        SystemMessage(content=(
            "Summarize this shopping conversation in 2-3 sentences. "
            "Focus on: what products were discussed, user preferences, "
            "and any items added to cart. Be specific about product names and prices."
        )),
        HumanMessage(content=conversation_text),
    ])

    return response.content
