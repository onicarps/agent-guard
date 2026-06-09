"""CrewAI integration — agent decorator for permission enforcement."""
from __future__ import annotations

import functools
from typing import Any, Callable

from agent_guard.engine import PermissionEngine


class CrewAIGuard:
    """CrewAI agent decorator for enforcing permissions."""

    def __init__(self, engine: PermissionEngine, agent_id: str):
        self.engine = engine
        self.agent_id = agent_id

    def guard_task(self, task_func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorate a CrewAI task to enforce permissions."""
        @functools.wraps(task_func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            task_name = task_func.__name__
            await self.engine.assert_allowed(
                agent_id=self.agent_id,
                resource=task_name,
                operation="execute",
            )
            return await task_func(*args, **kwargs)
        return wrapper

    def guard_task_sync(self, task_func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorate a synchronous CrewAI task."""
        @functools.wraps(task_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            task_name = task_func.__name__
            import asyncio
            asyncio.run(self.engine.assert_allowed(
                agent_id=self.agent_id,
                resource=task_name,
                operation="execute",
            ))
            return task_func(*args, **kwargs)
        return wrapper
