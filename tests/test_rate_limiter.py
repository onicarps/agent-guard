"""Tests for sliding window rate limiter (ONI-78)."""
from __future__ import annotations

import asyncio
import os
import tempfile
from unittest.mock import patch

import pytest
import pytest_asyncio

from agent_guard.engine import PermissionEngine
from agent_guard.policies import (
    AgentPolicy,
    PermissionEffect,
    ResourcePermission,
    ResourceType,
    ToolConstraint,
)
from agent_guard.rate_limiter import RateLimiter
from agent_guard.registry import AgentRegistry


@pytest_asyncio.fixture
async def registry():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    reg = AgentRegistry(db_path)
    await reg.connect()
    yield reg
    await reg.close()
    os.unlink(db_path)


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_within_limit(self):
        rl = RateLimiter()
        for _ in range(5):
            assert await rl.check("agent1", "tool1", max_per_hour=10) is True

    @pytest.mark.asyncio
    async def test_rate_limiter_denies_over_limit(self):
        rl = RateLimiter()
        for _ in range(10):
            assert await rl.check("agent1", "tool1", max_per_hour=10) is True
        assert await rl.check("agent1", "tool1", max_per_hour=10) is False

    @pytest.mark.asyncio
    async def test_rate_limiter_sliding_window(self):
        rl = RateLimiter()
        base = 1000.0
        with patch("agent_guard.rate_limiter.time.time", return_value=base):
            for _ in range(3):
                assert await rl.check("a", "r", max_per_hour=3) is True
            assert await rl.check("a", "r", max_per_hour=3) is False

        with patch("agent_guard.rate_limiter.time.time", return_value=base + 3601):
            assert await rl.check("a", "r", max_per_hour=3) is True

    @pytest.mark.asyncio
    async def test_rate_limiter_per_agent_isolated(self):
        rl = RateLimiter()
        for _ in range(2):
            assert await rl.check("a", "tool", max_per_hour=2) is True
        assert await rl.check("a", "tool", max_per_hour=2) is False
        assert await rl.check("b", "tool", max_per_hour=2) is True

    @pytest.mark.asyncio
    async def test_rate_limiter_per_resource_isolated(self):
        rl = RateLimiter()
        for _ in range(2):
            assert await rl.check("a", "tool1", max_per_hour=2) is True
        assert await rl.check("a", "tool1", max_per_hour=2) is False
        assert await rl.check("a", "tool2", max_per_hour=2) is True

    @pytest.mark.asyncio
    async def test_rate_limiter_no_constraints(self):
        rl = RateLimiter()
        for _ in range(100):
            assert await rl.check("a", "r") is True

    @pytest.mark.asyncio
    async def test_rate_limiter_day_window(self):
        rl = RateLimiter()
        base = 5000.0
        with patch("agent_guard.rate_limiter.time.time", return_value=base):
            for _ in range(2):
                assert await rl.check("a", "r", max_per_day=2) is True
            assert await rl.check("a", "r", max_per_day=2) is False

        with patch("agent_guard.rate_limiter.time.time", return_value=base + 1000):
            assert await rl.check("a", "r", max_per_day=2) is False

        with patch("agent_guard.rate_limiter.time.time", return_value=base + 86401):
            assert await rl.check("a", "r", max_per_day=2) is True


class TestEngineRateLimitIntegration:
    @pytest.mark.asyncio
    async def test_engine_integration_rate_limit(self, registry):
        policy = AgentPolicy(
            agent_name="rl-agent",
            permissions=[
                ResourcePermission(
                    name="capped",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                    constraints=ToolConstraint(max_per_hour=2),
                ),
            ],
        )
        agent_id = await registry.register_agent(policy)
        engine = PermissionEngine(registry)

        assert await engine.check(agent_id, "capped") == PermissionEffect.ALLOW
        assert await engine.check(agent_id, "capped") == PermissionEffect.ALLOW
        assert await engine.check(agent_id, "capped") == PermissionEffect.DENY

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_safety(self):
        """Concurrent calls should all count against the same window (W4)."""
        rl = RateLimiter()
        max_per_hour = 10

        # Fire 15 concurrent checks
        results = await asyncio.gather(*[
            rl.check("agent", "tool", max_per_hour=max_per_hour)
            for _ in range(15)
        ])

        # Exactly 10 should pass, 5 should be denied
        allowed = sum(1 for r in results if r is True)
        denied = sum(1 for r in results if r is False)

        assert allowed == 10, f"Expected 10 allowed, got {allowed}"
        assert denied == 5, f"Expected 5 denied, got {denied}"
