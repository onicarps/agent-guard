"""LangChain integration — middleware wrapper for agent tool calls."""
from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable

from agent_guard.engine import PermissionEngine


class LangChainGuard:
    """LangChain middleware for enforcing agent permissions."""

    def __init__(self, engine: PermissionEngine, agent_id: str):
        self.engine = engine
        self.agent_id = agent_id

    def guard_tool(self, tool_func: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap a LangChain tool to enforce permissions."""
        @functools.wraps(tool_func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tool_name = tool_func.__name__
            await self.engine.assert_allowed(
                agent_id=self.agent_id,
                resource=tool_name,
                operation="execute",
            )
            return await tool_func(*args, **kwargs)
        return wrapper

    def guard_tool_sync(self, tool_func: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap a synchronous LangChain tool."""
        @functools.wraps(tool_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tool_name = tool_func.__name__
            asyncio.run(self.engine.assert_allowed(
                agent_id=self.agent_id,
                resource=tool_name,
                operation="execute",
            ))
            return tool_func(*args, **kwargs)
        return wrapper


def create_guarded_agent(
    engine: PermissionEngine,
    agent_id: str,
    tools: list[Callable],
) -> list[Callable]:
    """Create a list of guarded tools for a LangChain agent."""
    guard = LangChainGuard(engine, agent_id)
    guarded_tools = []
    for tool in tools:
        if asyncio.iscoroutinefunction(tool):
            guarded_tools.append(guard.guard_tool(tool))
        else:
            guarded_tools.append(guard.guard_tool_sync(tool))
    return guarded_tools
