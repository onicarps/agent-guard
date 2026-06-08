"""Middleware base — intercepts agent tool calls."""
from __future__ import annotations

import functools
from typing import Any, Callable, Coroutine

from .engine import PermissionEngine, PermissionDeniedError


class GuardMiddleware:
    """Base middleware for enforcing agent permissions."""

    def __init__(self, engine: PermissionEngine):
        self.engine = engine

    async def guard_tool(
        self,
        agent_id: str,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
    ) -> None:
        """Check permission before executing a tool."""
        await self.engine.assert_allowed(
            agent_id=agent_id,
            resource=tool_name,
            operation="execute",
        )

    def guarded(self, agent_id: str, tool_name: str) -> Callable:
        """Decorator to guard a tool function."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                await self.guard_tool(agent_id, tool_name)
                return await func(*args, **kwargs)
            return wrapper
        return decorator
