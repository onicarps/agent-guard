import pytest
import pytest_asyncio
import tempfile
import os

from agent_guard.policies import (
    AgentPolicy,
    PermissionEffect,
    ResourcePermission,
    ResourceType,
    ToolConstraint,
    AuditEntry,
)
from agent_guard.registry import AgentRegistry
from agent_guard.engine import PermissionEngine, PermissionDeniedError


class TestAgentPolicy:
    """Test policy model."""

    def test_default_deny(self):
        policy = AgentPolicy(agent_name="test")
        assert policy.check_permission("any_resource") == PermissionEffect.DENY

    def test_allow(self):
        policy = AgentPolicy(
            agent_name="test",
            permissions=[
                ResourcePermission(
                    name="read_emails",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                )
            ],
        )
        assert policy.check_permission("read_emails") == PermissionEffect.ALLOW
        assert policy.check_permission("delete_emails") == PermissionEffect.DENY

    def test_deny_takes_precedence(self):
        policy = AgentPolicy(
            agent_name="test",
            permissions=[
                ResourcePermission(
                    name="database",
                    type=ResourceType.DATABASE,
                    effect=PermissionEffect.ALLOW,
                ),
                ResourcePermission(
                    name="database",
                    type=ResourceType.DATABASE,
                    effect=PermissionEffect.DENY,
                ),
            ],
        )
        assert policy.check_permission("database") == PermissionEffect.DENY

    def test_operation_constraint(self):
        policy = AgentPolicy(
            agent_name="test",
            permissions=[
                ResourcePermission(
                    name="database",
                    type=ResourceType.DATABASE,
                    effect=PermissionEffect.ALLOW,
                    constraints=ToolConstraint(allowed_operations=["read"]),
                ),
            ],
        )
        assert policy.check_permission("database", "read") == PermissionEffect.ALLOW
        assert policy.check_permission("database", "write") == PermissionEffect.DENY


class TestAgentRegistry:
    """Test agent registry."""

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
    async def test_register_and_get(self, registry):
        policy = AgentPolicy(agent_name="test-agent", role="developer")
        agent_id = await registry.register_agent(policy)

        retrieved = await registry.get_agent(agent_id)
        assert retrieved is not None
        assert retrieved.agent_name == "test-agent"
        assert retrieved.role == "developer"

    @pytest.mark.asyncio
    async def test_list_agents(self, registry):
        await registry.register_agent(AgentPolicy(agent_name="agent-1"))
        await registry.register_agent(AgentPolicy(agent_name="agent-2"))

        agents = await registry.list_agents()
        assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_check_permission(self, registry):
        policy = AgentPolicy(
            agent_name="test",
            permissions=[
                ResourcePermission(
                    name="read_emails",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        agent_id = await registry.register_agent(policy)

        effect = await registry.check_permission(agent_id, "read_emails")
        assert effect == PermissionEffect.ALLOW

        effect = await registry.check_permission(agent_id, "delete_emails")
        assert effect == PermissionEffect.DENY

    @pytest.mark.asyncio
    async def test_audit_log(self, registry):
        entry = AuditEntry(
            agent_id="test-id",
            agent_name="test",
            resource="read_emails",
            effect=PermissionEffect.ALLOW,
        )
        await registry.log_audit(entry)

        logs = await registry.get_audit_log(limit=1)
        assert len(logs) == 1
        assert logs[0]["resource"] == "read_emails"


class TestPermissionEngine:
    """Test permission engine."""

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
    async def test_check_and_log(self, engine):
        eng, reg, _ = engine
        policy = AgentPolicy(agent_name="test")
        agent_id = await reg.register_agent(policy)

        effect = await eng.check(agent_id, "some_resource")
        assert effect == PermissionEffect.DENY

        # Verify audit log
        logs = await reg.get_audit_log(agent_id)
        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_assert_allowed_raises(self, engine):
        eng, reg, _ = engine
        policy = AgentPolicy(agent_name="test")
        agent_id = await reg.register_agent(policy)

        with pytest.raises(PermissionDeniedError):
            await eng.assert_allowed(agent_id, "unauthorized_resource")

    @pytest.mark.asyncio
    async def test_assert_allowed_passes(self, engine):
        eng, reg, _ = engine
        policy = AgentPolicy(
            agent_name="test",
            permissions=[
                ResourcePermission(
                    name="allowed_tool",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        agent_id = await reg.register_agent(policy)

        # Should not raise
        await eng.assert_allowed(agent_id, "allowed_tool")
