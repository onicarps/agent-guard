"""Tests for permission inheritance (ONI-77)."""
from __future__ import annotations

import os
import tempfile

import pytest
import pytest_asyncio

from agent_guard.engine import PermissionEngine
from agent_guard.policies import (
    AgentPolicy,
    PermissionEffect,
    ResourcePermission,
    ResourceType,
)
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


class TestPermissionInheritance:
    @pytest.mark.asyncio
    async def test_inheritance_basic(self, registry):
        parent = AgentPolicy(
            agent_name="parent",
            permissions=[
                ResourcePermission(
                    name="read_db",
                    type=ResourceType.DATABASE,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        parent_id = await registry.register_agent(parent)

        child = AgentPolicy(agent_name="child", parent_agent_id=parent_id)
        child_id = await registry.register_agent(child)

        engine = PermissionEngine(registry)
        effect = await engine.check(child_id, "read_db")
        assert effect == PermissionEffect.ALLOW

    @pytest.mark.asyncio
    async def test_inheritance_child_override(self, registry):
        parent = AgentPolicy(
            agent_name="parent",
            permissions=[
                ResourcePermission(
                    name="read_db",
                    type=ResourceType.DATABASE,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        parent_id = await registry.register_agent(parent)

        child = AgentPolicy(
            agent_name="child",
            parent_agent_id=parent_id,
            permissions=[
                ResourcePermission(
                    name="read_db",
                    type=ResourceType.DATABASE,
                    effect=PermissionEffect.DENY,
                ),
            ],
        )
        child_id = await registry.register_agent(child)

        engine = PermissionEngine(registry)
        effect = await engine.check(child_id, "read_db")
        assert effect == PermissionEffect.DENY

    @pytest.mark.asyncio
    async def test_inheritance_chain(self, registry):
        grand = AgentPolicy(
            agent_name="grand",
            permissions=[
                ResourcePermission(
                    name="root_only",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        grand_id = await registry.register_agent(grand)

        parent = AgentPolicy(agent_name="parent", parent_agent_id=grand_id)
        parent_id = await registry.register_agent(parent)

        child = AgentPolicy(agent_name="child", parent_agent_id=parent_id)
        child_id = await registry.register_agent(child)

        engine = PermissionEngine(registry)
        effect = await engine.check(child_id, "root_only")
        assert effect == PermissionEffect.ALLOW

    @pytest.mark.asyncio
    async def test_inheritance_circular(self, registry):
        a = AgentPolicy(agent_name="a")
        a_id = await registry.register_agent(a)

        b = AgentPolicy(agent_name="b", parent_agent_id=a_id)
        b_id = await registry.register_agent(b)

        a.parent_agent_id = b_id
        await registry.update_policy(a_id, a)

        perms = await registry.resolve_permissions(a_id)
        assert perms == []

        engine = PermissionEngine(registry)
        effect = await engine.check(a_id, "anything")
        assert effect == PermissionEffect.DENY

    @pytest.mark.asyncio
    async def test_inheritance_no_parent(self, registry):
        policy = AgentPolicy(
            agent_name="solo",
            permissions=[
                ResourcePermission(
                    name="tool_x",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        agent_id = await registry.register_agent(policy)

        engine = PermissionEngine(registry)
        assert await engine.check(agent_id, "tool_x") == PermissionEffect.ALLOW
        assert await engine.check(agent_id, "tool_y") == PermissionEffect.DENY

    @pytest.mark.asyncio
    async def test_inheritance_parent_not_found(self, registry):
        child = AgentPolicy(
            agent_name="orphan",
            parent_agent_id="non-existent-id",
            permissions=[
                ResourcePermission(
                    name="own_tool",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        child_id = await registry.register_agent(child)

        engine = PermissionEngine(registry)
        assert await engine.check(child_id, "own_tool") == PermissionEffect.ALLOW
        assert await engine.check(child_id, "missing") == PermissionEffect.DENY
