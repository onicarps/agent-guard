"""Tests for YAML policy templates (S1)."""
from __future__ import annotations

import os

import pytest
import yaml

from agent_guard.policies import AgentPolicy


TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


class TestTemplates:
    """Verify all shipped YAML templates parse and validate correctly."""

    def _load_template(self, name: str) -> dict:
        path = os.path.join(TEMPLATES_DIR, name)
        with open(path) as f:
            return yaml.safe_load(f)

    def test_read_only_template_parses(self):
        data = self._load_template("read_only.yaml")
        assert data["agent_name"] == "{{name}}"
        assert data["role"] == "read_only"
        assert len(data["permissions"]) == 5

    def test_developer_template_parses(self):
        data = self._load_template("developer.yaml")
        assert data["agent_name"] == "{{name}}"
        assert data["role"] == "developer"
        assert data["escalation"]["enabled"] is True
        assert data["escalation"]["approver"] == "tech-lead"

    def test_admin_template_parses(self):
        data = self._load_template("admin.yaml")
        assert data["agent_name"] == "{{name}}"
        assert data["role"] == "admin"
        assert len(data["permissions"]) == 5

    def test_read_only_template_validates(self):
        data = self._load_template("read_only.yaml")
        data["agent_name"] = "test-agent"  # substitute placeholder
        policy = AgentPolicy(**data)
        assert policy.agent_name == "test-agent"
        assert policy.role == "read_only"

    def test_developer_template_validates(self):
        data = self._load_template("developer.yaml")
        data["agent_name"] = "test-agent"
        policy = AgentPolicy(**data)
        assert policy.agent_name == "test-agent"
        assert policy.escalation.enabled is True

    def test_admin_template_validates(self):
        data = self._load_template("admin.yaml")
        data["agent_name"] = "test-agent"
        policy = AgentPolicy(**data)
        assert policy.agent_name == "test-agent"
        assert len(policy.permissions) == 5

    def test_all_templates_have_required_fields(self):
        for template_name in ["read_only.yaml", "developer.yaml", "admin.yaml"]:
            data = self._load_template(template_name)
            assert "agent_name" in data
            assert "role" in data
            assert "permissions" in data
            assert isinstance(data["permissions"], list)
            assert len(data["permissions"]) > 0

    def test_all_template_permissions_have_required_fields(self):
        for template_name in ["read_only.yaml", "developer.yaml", "admin.yaml"]:
            data = self._load_template(template_name)
            for perm in data["permissions"]:
                assert "name" in perm
                assert "type" in perm
                assert "effect" in perm
                assert perm["effect"] in ("allow", "deny")
