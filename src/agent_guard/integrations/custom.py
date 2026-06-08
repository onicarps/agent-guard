"""Custom agent decorator — for any agent framework."""
from __future__ import annotations

import functools
from typing import Any, Callable

from agent_guard.engine import PermissionEngine


def guarded(engine: PermissionEngine, agent_id: str, resource: str | None = None):
    """Decorator to guard any agent function with permission checking.

    Usage:
        @guarded(engine, agent_id="agent-1", resource="send_email")
        async def send_email(to: str, subject: str, body: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            res = resource or func.__name__
            await engine.assert_allowed(agent_id, res, "execute")
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            res = resource or func.__name__
            # For sync functions, we need to run the async check in a new loop
            import asyncio
            try:
                asyncio.get_running_loop()
                # We're inside an async context — can't use asyncio.run()
                # Create a new thread to run the check
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, engine.assert_allowed(agent_id, res, "execute"))
                    future.result(timeout=5)
            except RuntimeError:
                # No running loop — safe to use asyncio.run()
                asyncio.run(engine.assert_allowed(agent_id, res, "execute"))
            return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
