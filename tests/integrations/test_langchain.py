"""Tests for the LangChain integration."""
from __future__ import annotations

import asyncio
import os
import tempfile

import pytest
import pytest_asyncio

from agent_guard.engine import PermissionDeniedError, PermissionEngine
from agent_guard.integrations.langchain import LangChainGuard, create_guarded_agent
from agent_guard.policies import (
    AgentPolicy,
    PermissionEffect,
    ResourcePermission,
    ResourceType,
)
from agent_guard.registry import AgentRegistry


def _allow_policy(name: str, *resources: str) -> AgentPolicy:
    return AgentPolicy(
        agent_name=name,
        permissions=[
            ResourcePermission(
                name=resource,
                type=ResourceType.TOOL,
                effect=PermissionEffect.ALLOW,
            )
            for resource in resources
        ],
    )


class TestLangChainGuardAsync:
    @pytest_asyncio.fixture
    async def engine(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        reg = AgentRegistry(db_path)
        await reg.connect()
        eng = PermissionEngine(reg)
        yield eng, reg, db_path
        await reg.close()
        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_guard_tool_allows(self, engine):
        eng, reg, _ = engine
        agent_id = await reg.register_agent(_allow_policy("t", "fetch_data"))
        guard = LangChainGuard(eng, agent_id)

        async def fetch_data(x):
            return x * 2

        wrapped = guard.guard_tool(fetch_data)
        assert await wrapped(7) == 14

    @pytest.mark.asyncio
    async def test_guard_tool_denies(self, engine):
        eng, reg, _ = engine
        agent_id = await reg.register_agent(AgentPolicy(agent_name="t"))
        guard = LangChainGuard(eng, agent_id)

        async def fetch_data():
            return "secret"

        wrapped = guard.guard_tool(fetch_data)
        with pytest.raises(PermissionDeniedError):
            await wrapped()

    @pytest.mark.asyncio
    async def test_guarded_tool_preserves_name(self, engine):
        eng, reg, _ = engine
        agent_id = await reg.register_agent(_allow_policy("t", "named_tool"))
        guard = LangChainGuard(eng, agent_id)

        async def named_tool():
            return "ok"

        wrapped = guard.guard_tool(named_tool)
        assert wrapped.__name__ == "named_tool"


class TestLangChainGuardSync:
    """Sync wrappers run their own asyncio.run, so use a sync fixture."""

    @pytest.fixture
    def engine(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        reg = AgentRegistry(db_path)
        asyncio.run(reg.connect())
        eng = PermissionEngine(reg)
        yield eng, reg
        asyncio.run(reg.close())

    def test_guard_tool_sync_allows(self, engine):
        eng, reg = engine
        agent_id = asyncio.run(reg.register_agent(_allow_policy("t", "sync_fetch")))
        guard = LangChainGuard(eng, agent_id)

        def sync_fetch(x):
            return x + 1

        wrapped = guard.guard_tool_sync(sync_fetch)
        assert wrapped(4) == 5

    def test_guard_tool_sync_denies(self, engine):
        eng, reg = engine
        agent_id = asyncio.run(reg.register_agent(AgentPolicy(agent_name="t")))
        guard = LangChainGuard(eng, agent_id)

        def sync_fetch():
            return "nope"

        wrapped = guard.guard_tool_sync(sync_fetch)
        with pytest.raises(PermissionDeniedError):
            wrapped()


class TestCreateGuardedAgent:
    @pytest.fixture
    def engine(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        reg = AgentRegistry(db_path)
        asyncio.run(reg.connect())
        eng = PermissionEngine(reg)
        yield eng, reg
        asyncio.run(reg.close())

    def test_create_guarded_agent_mixed(self, engine):
        eng, reg = engine
        agent_id = asyncio.run(
            reg.register_agent(_allow_policy("t", "async_tool", "sync_tool"))
        )

        async def async_tool():
            return "async-ok"

        def sync_tool():
            return "sync-ok"

        wrapped = create_guarded_agent(eng, agent_id, [async_tool, sync_tool])
        assert len(wrapped) == 2

        async_wrapped, sync_wrapped = wrapped
        assert asyncio.iscoroutinefunction(async_wrapped)
        assert not asyncio.iscoroutinefunction(sync_wrapped)

        assert sync_wrapped() == "sync-ok"
        assert asyncio.run(async_wrapped()) == "async-ok"

    def test_create_guarded_agent_all_async(self, engine):
        eng, reg = engine
        agent_id = asyncio.run(
            reg.register_agent(_allow_policy("t", "first", "second"))
        )

        async def first():
            return 1

        async def second():
            return 2

        wrapped = create_guarded_agent(eng, agent_id, [first, second])
        assert all(asyncio.iscoroutinefunction(w) for w in wrapped)
        assert wrapped[0].__name__ == "first"
        assert wrapped[1].__name__ == "second"
        assert asyncio.run(wrapped[0]()) == 1
        assert asyncio.run(wrapped[1]()) == 2
