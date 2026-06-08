"""Sliding window rate limiter for per-agent, per-resource enforcement."""
from __future__ import annotations

import time

HOUR_SECONDS = 3600
DAY_SECONDS = 86400


class RateLimiter:
    """In-memory sliding window rate limiter, per-agent per-resource."""

    def __init__(self) -> None:
        self._windows: dict[tuple[str, str], list[float]] = {}

    def check(
        self,
        agent_id: str,
        resource: str,
        max_per_hour: int | None = None,
        max_per_day: int | None = None,
    ) -> bool:
        """Returns True if within rate limit, False if exceeded.

        Records the current timestamp on success so subsequent calls
        decrement the available budget.
        """
        if max_per_hour is None and max_per_day is None:
            return True

        now = time.time()
        key = (agent_id, resource)
        timestamps = self._windows.setdefault(key, [])

        cutoff = now - DAY_SECONDS if max_per_day is not None else now - HOUR_SECONDS
        timestamps[:] = [t for t in timestamps if t > cutoff]

        if max_per_hour is not None:
            hour_cutoff = now - HOUR_SECONDS
            hour_count = sum(1 for t in timestamps if t > hour_cutoff)
            if hour_count >= max_per_hour:
                return False

        if max_per_day is not None:
            day_cutoff = now - DAY_SECONDS
            day_count = sum(1 for t in timestamps if t > day_cutoff)
            if day_count >= max_per_day:
                return False

        timestamps.append(now)
        return True
