"""
Request-scoped context for the agent.

contextvars is Python's version of Node.js AsyncLocalStorage.
It lets you store per-request data (like db session, user_id)
that any function in the call stack can access — without passing
it through every function argument.

We use this to inject db and user_id into tools without putting
them in the LangGraph state (which Pydantic can't serialize).
"""
from contextvars import ContextVar
from sqlalchemy.ext.asyncio import AsyncSession

db_var: ContextVar[AsyncSession] = ContextVar("db")
user_id_var: ContextVar[str] = ContextVar("user_id")
