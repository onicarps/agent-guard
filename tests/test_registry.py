"""Tests for AgentRegistry edge cases."""
from __future__ import annotations

import os
import tempfile

import pytest
import pytest_asyncio

from agent_guard.policies import (
    AgentPolicy,
    AuditEntry,
    PermissionEffect,
    ResourcePermission,
    ResourceType,
)
from agent_guard.registry import AgentRegistry


class TestRegistryEdgeCases:
    @pytest_asyncio.fixture
    async def registry(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        reg = AgentRegistry(db_path)
        await reg.connect()
        yield reg
        await reg.close()
        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_get_agent_by_name(self, registry):
        policy = AgentPolicy(agent_name="findme", role="ops")
        await registry.register_agent(policy)

        retrieved = await registry.get_agent_by_name("findme")
        assert retrieved is not None
        assert retrieved.agent_name == "findme"
        assert retrieved.role == "ops"

    @pytest.mark.asyncio
    async def test_get_agent_by_name_not_found(self, registry):
        result = await registry.get_agent_by_name("missing-agent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_policy(self, registry):
        agent_id = await registry.register_agent(AgentPolicy(agent_name="t"))

        new_policy = AgentPolicy(
            agent_id=agent_id,
            agent_name="t",
            role="upgraded",
            permissions=[
                ResourcePermission(
                    name="new_tool",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        ok = await registry.update_policy(agent_id, new_policy)
        assert ok is True

        retrieved = await registry.get_agent(agent_id)
        assert retrieved is not None
        assert retrieved.role == "upgraded"
        assert retrieved.check_permission("new_tool") == PermissionEffect.ALLOW

    @pytest.mark.asyncio
    async def test_update_policy_not_found(self, registry):
        ok = await registry.update_policy(
            "nope", AgentPolicy(agent_name="ghost")
        )
        assert ok is False

    @pytest.mark.asyncio
    async def test_delete_agent(self, registry):
        agent_id = await registry.register_agent(AgentPolicy(agent_name="t"))

        ok = await registry.delete_agent(agent_id)
        assert ok is True
        assert await registry.get_agent(agent_id) is None

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, registry):
        ok = await registry.delete_agent("nonexistent")
        assert ok is False

    @pytest.mark.asyncio
    async def test_get_audit_log_by_agent(self, registry):
        a_id = await registry.register_agent(AgentPolicy(agent_name="a"))
        b_id = await registry.register_agent(AgentPolicy(agent_name="b"))

        for resource in ("r1", "r2"):
            await registry.log_audit(
                AuditEntry(
                    agent_id=a_id,
                    agent_name="a",
                    resource=resource,
                    effect=PermissionEffect.ALLOW,
                )
            )
        await registry.log_audit(
            AuditEntry(
                agent_id=b_id,
                agent_name="b",
                resource="r3",
                effect=PermissionEffect.DENY,
            )
        )

        a_logs = await registry.get_audit_log(a_id)
        assert len(a_logs) == 2
        assert all(entry["agent_id"] == a_id for entry in a_logs)

        b_logs = await registry.get_audit_log(b_id)
        assert len(b_logs) == 1
        assert b_logs[0]["agent_id"] == b_id

    @pytest.mark.asyncio
    async def test_get_audit_log_limit(self, registry):
        agent_id = await registry.register_agent(AgentPolicy(agent_name="lots"))
        for i in range(5):
            await registry.log_audit(
                AuditEntry(
                    agent_id=agent_id,
                    agent_name="lots",
                    resource=f"r{i}",
                    effect=PermissionEffect.ALLOW,
                )
            )

        logs = await registry.get_audit_log(agent_id, limit=3)
        assert len(logs) == 3
