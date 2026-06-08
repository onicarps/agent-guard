"""Tests for PermissionEngine.request_escalation."""
from __future__ import annotations

import os
import tempfile

import pytest
import pytest_asyncio

from agent_guard.engine import PermissionEngine
from agent_guard.policies import AgentPolicy, EscalationPolicy
from agent_guard.registry import AgentRegistry


class TestEngineEscalation:
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
    async def test_escalation_disabled_by_default(self, engine):
        eng, reg, _ = engine
        agent_id = await reg.register_agent(AgentPolicy(agent_name="t"))

        approved = await eng.request_escalation(agent_id, "secret_resource", "need it")
        assert approved is False

    @pytest.mark.asyncio
    async def test_escalation_enabled_but_not_auto_approved(self, engine):
        eng, reg, _ = engine
        policy = AgentPolicy(
            agent_name="t",
            escalation=EscalationPolicy(enabled=True, approver="ops@example.com"),
        )
        agent_id = await reg.register_agent(policy)

        approved = await eng.request_escalation(agent_id, "secret_resource", "need it")
        assert approved is False

    @pytest.mark.asyncio
    async def test_escalation_logs_audit_entry(self, engine):
        eng, reg, _ = engine
        policy = AgentPolicy(
            agent_name="t",
            escalation=EscalationPolicy(enabled=True, approver="ops@example.com"),
        )
        agent_id = await reg.register_agent(policy)

        await eng.request_escalation(agent_id, "secret_resource", "investigation")

        logs = await reg.get_audit_log(agent_id)
        assert len(logs) == 1
        assert logs[0]["operation"] == "escalation_request"
        assert logs[0]["resource"] == "secret_resource"

    @pytest.mark.asyncio
    async def test_escalation_with_nonexistent_agent(self, engine):
        eng, _reg, _ = engine

        approved = await eng.request_escalation("does-not-exist", "anything", "reason")
        assert approved is False
