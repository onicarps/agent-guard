"""Policy models for agent-guard."""
from __future__ import annotations

import enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PermissionEffect(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"


class ResourceType(str, enum.Enum):
    TOOL = "tool"
    API = "api"
    DATABASE = "database"
    FILE = "file"
    EMAIL = "email"
    PAYMENT = "payment"


class ToolConstraint(BaseModel):
    """Constraints on tool usage."""
    max_per_hour: int | None = None
    max_per_day: int | None = None
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_tables: list[str] = Field(default_factory=list)
    allowed_operations: list[str] = Field(default_factory=list)  # read, write, delete


class ResourcePermission(BaseModel):
    """Permission for a specific resource."""
    name: str
    type: ResourceType
    effect: PermissionEffect
    constraints: ToolConstraint = Field(default_factory=ToolConstraint)


class EscalationPolicy(BaseModel):
    """Dynamic permission escalation."""
    enabled: bool = False
    approver: str | None = None  # Who can approve escalation
    max_escalations_per_day: int = 3
    auto_approve_after_minutes: int | None = None  # Auto-approve if no response


class AgentPolicy(BaseModel):
    """Complete policy for an agent."""
    agent_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str
    role: str = "default"
    permissions: list[ResourcePermission] = Field(default_factory=list)
    escalation: EscalationPolicy = Field(default_factory=EscalationPolicy)
    parent_agent_id: str | None = None  # For permission inheritance

    def check_permission(
        self,
        resource_name: str,
        operation: str | None = None,
        inherited_permissions: list[ResourcePermission] | None = None,
    ) -> PermissionEffect:
        """Check if agent has permission for a resource."""
        # Explicit deny on own permissions takes precedence over everything
        for perm in self.permissions:
            if perm.name == resource_name and perm.effect == PermissionEffect.DENY:
                return PermissionEffect.DENY

        for perm in self.permissions:
            if perm.name == resource_name and perm.effect == PermissionEffect.ALLOW:
                if operation and perm.constraints.allowed_operations:
                    if operation not in perm.constraints.allowed_operations:
                        return PermissionEffect.DENY
                return PermissionEffect.ALLOW

        if inherited_permissions:
            for perm in inherited_permissions:
                if perm.name == resource_name and perm.effect == PermissionEffect.DENY:
                    return PermissionEffect.DENY
            for perm in inherited_permissions:
                if perm.name == resource_name and perm.effect == PermissionEffect.ALLOW:
                    if operation and perm.constraints.allowed_operations:
                        if operation not in perm.constraints.allowed_operations:
                            return PermissionEffect.DENY
                    return PermissionEffect.ALLOW

        return PermissionEffect.DENY


class AuditEntry(BaseModel):
    """Single audit log entry."""
    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    agent_name: str
    resource: str
    operation: str | None = None
    effect: PermissionEffect
    timestamp: float = Field(default_factory=lambda: __import__('time').time())
    metadata: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str = ""
