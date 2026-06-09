"""Tests for the agent-guard CLI."""
from __future__ import annotations

import asyncio
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from agent_guard.cli import app
from agent_guard.engine import PermissionEngine
from agent_guard.policies import (
    AgentPolicy,
    PermissionEffect,
    ResourcePermission,
    ResourceType,
)
from agent_guard.registry import AgentRegistry

runner = CliRunner()


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """Run each CLI test in an isolated tmp dir so the default DB is sandboxed."""
    monkeypatch.chdir(tmp_path)
    yield tmp_path


def _seed_agent(policy: AgentPolicy) -> str:
    async def _seed() -> str:
        registry = AgentRegistry()
        await registry.connect()
        try:
            return await registry.register_agent(policy)
        finally:
            await registry.close()

    return asyncio.run(_seed())


def _seed_audit_check(agent_id: str, resource: str) -> None:
    async def _go() -> None:
        registry = AgentRegistry()
        await registry.connect()
        try:
            engine = PermissionEngine(registry)
            await engine.check(agent_id, resource)
        finally:
            await registry.close()

    asyncio.run(_go())


class TestMainBlock:
    """Test the __main__ entry point (S7)."""

    def test_main_block_help(self, cli_env):
        """Running the module via python -m should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "agent_guard.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=str(cli_env),
        )
        assert result.returncode == 0
        assert "Agent-Guard" in result.stdout
        assert "register" in result.stdout
        assert "check" in result.stdout
        assert "list" in result.stdout
        assert "audit" in result.stdout
        assert "delete" in result.stdout


class TestRegisterCommand:
    def test_register_with_name_only(self, cli_env):
        result = runner.invoke(app, ["register", "--name", "test-agent"])
        assert result.exit_code == 0
        assert "Registered agent" in result.stdout
        assert "test-agent" in result.stdout

    def test_register_with_policy_file(self, cli_env):
        policy_file = cli_env / "policy.yaml"
        policy_file.write_text(
            "agent_name: yaml-agent\n"
            "role: read_only\n"
            "permissions:\n"
            "  - name: database\n"
            "    type: database\n"
            "    effect: allow\n"
            "    constraints:\n"
            "      allowed_operations: [read]\n"
        )
        result = runner.invoke(
            app,
            [
                "register",
                "--name",
                "yaml-agent",
                "--policy-file",
                str(policy_file),
            ],
        )
        assert result.exit_code == 0
        assert "Registered agent" in result.stdout

    def test_register_invalid_yaml(self, cli_env):
        bad = cli_env / "bad.yaml"
        bad.write_text("agent_name: x\n  bad: [unclosed\n   key\n")
        result = runner.invoke(
            app,
            [
                "register",
                "--name",
                "x",
                "--policy-file",
                str(bad),
            ],
        )
        assert result.exit_code != 0
        assert result.exception is not None


class TestCheckCommand:
    def test_check_allow(self, cli_env):
        policy = AgentPolicy(
            agent_name="allow-agent",
            permissions=[
                ResourcePermission(
                    name="read_emails",
                    type=ResourceType.TOOL,
                    effect=PermissionEffect.ALLOW,
                ),
            ],
        )
        agent_id = _seed_agent(policy)

        result = runner.invoke(
            app,
            ["check", "--agent-id", agent_id, "--resource", "read_emails"],
        )
        assert result.exit_code == 0
        assert "ALLOW" in result.stdout

    def test_check_deny(self, cli_env):
        agent_id = _seed_agent(AgentPolicy(agent_name="deny-agent"))

        result = runner.invoke(
            app,
            ["check", "--agent-id", agent_id, "--resource", "delete_db"],
        )
        assert result.exit_code == 0
        assert "DENY" in result.stdout

    def test_check_unknown_agent(self, cli_env):
        result = runner.invoke(
            app,
            ["check", "--agent-id", "nonexistent-id", "--resource", "anything"],
        )
        assert result.exit_code == 0
        assert "DENY" in result.stdout


class TestListCommand:
    def test_list_empty(self, cli_env):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No agents registered" in result.stdout

    def test_list_with_agents(self, cli_env):
        _seed_agent(AgentPolicy(agent_name="alpha", role="dev"))
        _seed_agent(AgentPolicy(agent_name="beta", role="ops"))

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "alpha" in result.stdout
        assert "beta" in result.stdout


class TestAuditCommand:
    def test_audit_empty(self, cli_env):
        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        assert "No audit entries" in result.stdout

    def test_audit_with_entries(self, cli_env):
        agent_id = _seed_agent(
            AgentPolicy(
                agent_name="audited",
                permissions=[
                    ResourcePermission(
                        name="resource_a",
                        type=ResourceType.TOOL,
                        effect=PermissionEffect.ALLOW,
                    ),
                ],
            )
        )
        _seed_audit_check(agent_id, "resource_a")

        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        assert "audited" in result.stdout
        assert "resource_a" in result.stdout


class TestDeleteCommand:
    def test_delete_agent(self, cli_env):
        agent_id = _seed_agent(AgentPolicy(agent_name="to-delete"))

        result = runner.invoke(
            app,
            ["delete", "--agent-id", agent_id],
        )
        assert result.exit_code == 0
        assert "Deleted agent" in result.stdout

    def test_delete_nonexistent(self, cli_env):
        result = runner.invoke(
            app,
            ["delete", "--agent-id", "nonexistent-id"],
        )
        assert result.exit_code == 0
        assert "not found" in result.stdout
