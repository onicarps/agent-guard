"""Tests for GuardMiddleware."""
from __future__ import annotations

import os
import tempfile

import pytest
import pytest_asyncio

from agent_guard.engine import PermissionDeniedError, PermissionEngine
from agent_guard.middleware import GuardMiddleware
from agent_guard.policies import (
    AgentPolicy,
    PermissionEffect,
    ResourcePermission,
    ResourceType,
)
from agent_guard.registry import AgentRegistry


class TestGuardMiddleware:
    @pytest_asyncio.fixture
    async def setup(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        reg = AgentRegistry(db_path)
        await reg.connect()
        eng = PermissionEngine(reg)
        gm = GuardMiddleware(eng)
        yield gm, eng, reg
        await reg.close()
        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_guard_tool_allows(self, setup):
        gm, _eng, reg = setup
        policy = AgentPolicy(
            agent_name="t",
            permissions=[
                ResourcePermission(
                    name="my_tool",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        agent_id = await reg.register_agent(policy)

        await gm.guard_tool(agent_id, "my_tool")

    @pytest.mark.asyncio
    async def test_guard_tool_denies(self, setup):
        gm, _eng, reg = setup
        agent_id = await reg.register_agent(AgentPolicy(agent_name="t"))

        with pytest.raises(PermissionDeniedError):
            await gm.guard_tool(agent_id, "forbidden_tool")

    @pytest.mark.asyncio
    async def test_guarded_decorator_async(self, setup):
        gm, _eng, reg = setup
        policy = AgentPolicy(
            agent_name="t",
            permissions=[
                ResourcePermission(
                    name="async_tool",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        agent_id = await reg.register_agent(policy)

        @gm.guarded(agent_id, "async_tool")
        async def async_tool():
            return "ok"

        result = await async_tool()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_guarded_decorator_async_denies(self, setup):
        gm, _eng, reg = setup
        agent_id = await reg.register_agent(AgentPolicy(agent_name="t"))

        @gm.guarded(agent_id, "denied_tool")
        async def async_tool():
            return "should not reach"

        with pytest.raises(PermissionDeniedError):
            await async_tool()

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="GuardMiddleware.guarded only emits async wrappers; sync function "
        "support is a Mission 2 fix.",
        raises=TypeError,
    )
    async def test_guarded_decorator_sync(self, setup):
        gm, _eng, reg = setup
        policy = AgentPolicy(
            agent_name="t",
            permissions=[
                ResourcePermission(
                    name="sync_tool",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        agent_id = await reg.register_agent(policy)

        @gm.guarded(agent_id, "sync_tool")
        def sync_tool():
            return "ok"

        result = await sync_tool()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_guarded_decorator_sync_denies(self, setup):
        gm, _eng, reg = setup
        agent_id = await reg.register_agent(AgentPolicy(agent_name="t"))

        @gm.guarded(agent_id, "denied_sync_tool")
        def sync_tool():
            return "should not reach"

        with pytest.raises(PermissionDeniedError):
            await sync_tool()
