"""Tests for framework integrations."""
import pytest
import pytest_asyncio
import tempfile
import os

from agent_guard.policies import AgentPolicy, PermissionEffect, ResourcePermission, ResourceType
from agent_guard.registry import AgentRegistry
from agent_guard.engine import PermissionEngine, PermissionDeniedError
from agent_guard.integrations.custom import guarded


class TestCustomDecorator:
    """Test the custom @guarded decorator."""

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
    async def test_guarded_allows(self, engine):
        eng, reg, _ = engine
        policy = AgentPolicy(
            agent_name="test",
            permissions=[
                ResourcePermission(
                    name="my_tool",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        agent_id = await reg.register_agent(policy)

        @guarded(eng, agent_id, "my_tool")
        async def my_tool():
            return "success"

        result = await my_tool()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_guarded_denies(self, engine):
        eng, reg, _ = engine
        policy = AgentPolicy(agent_name="test")
        agent_id = await reg.register_agent(policy)

        @guarded(eng, agent_id, "unauthorized_tool")
        async def unauthorized_tool():
            return "should not reach"

        with pytest.raises(PermissionDeniedError):
            await unauthorized_tool()

    @pytest.mark.asyncio
    async def test_guarded_sync(self, engine):
        eng, reg, _ = engine
        policy = AgentPolicy(
            agent_name="test",
            permissions=[
                ResourcePermission(
                    name="sync_tool",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        agent_id = await reg.register_agent(policy)

        @guarded(eng, agent_id, "sync_tool")
        def sync_tool():
            return "sync success"

        result = sync_tool()
        assert result == "sync success"
