"""Tests for the CrewAI integration."""
from __future__ import annotations

import asyncio
import os
import tempfile

import pytest
import pytest_asyncio

from agent_guard.engine import PermissionDeniedError, PermissionEngine
from agent_guard.integrations.crewai import CrewAIGuard
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


class TestCrewAIGuardAsync:
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
    async def test_guard_task_allows(self, engine):
        eng, reg, _ = engine
        agent_id = await reg.register_agent(_allow_policy("t", "research"))
        guard = CrewAIGuard(eng, agent_id)

        async def research(topic):
            return f"results for {topic}"

        wrapped = guard.guard_task(research)
        assert await wrapped("crewai") == "results for crewai"

    @pytest.mark.asyncio
    async def test_guard_task_denies(self, engine):
        eng, reg, _ = engine
        agent_id = await reg.register_agent(AgentPolicy(agent_name="t"))
        guard = CrewAIGuard(eng, agent_id)

        async def research():
            return "secret"

        wrapped = guard.guard_task(research)
        with pytest.raises(PermissionDeniedError):
            await wrapped()

    @pytest.mark.asyncio
    async def test_guarded_task_preserves_name(self, engine):
        eng, reg, _ = engine
        agent_id = await reg.register_agent(_allow_policy("t", "named_task"))
        guard = CrewAIGuard(eng, agent_id)

        async def named_task():
            return "ok"

        wrapped = guard.guard_task(named_task)
        assert wrapped.__name__ == "named_task"


class TestCrewAIGuardSync:
    @pytest.fixture
    def engine(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        reg = AgentRegistry(db_path)
        asyncio.run(reg.connect())
        eng = PermissionEngine(reg)
        yield eng, reg
        asyncio.run(reg.close())

    def test_guard_task_sync_allows(self, engine):
        eng, reg = engine
        agent_id = asyncio.run(reg.register_agent(_allow_policy("t", "sync_task")))
        guard = CrewAIGuard(eng, agent_id)

        def sync_task(x):
            return x * 3

        wrapped = guard.guard_task_sync(sync_task)
        assert wrapped(2) == 6

    def test_guard_task_sync_denies(self, engine):
        eng, reg = engine
        agent_id = asyncio.run(reg.register_agent(AgentPolicy(agent_name="t")))
        guard = CrewAIGuard(eng, agent_id)

        def sync_task():
            return "nope"

        wrapped = guard.guard_task_sync(sync_task)
        with pytest.raises(PermissionDeniedError):
            wrapped()
