"""Permission engine — enforces agent permissions."""
from __future__ import annotations

import time
from typing import Any

from .policies import AgentPolicy, AuditEntry, PermissionEffect, ResourceType
from .registry import AgentRegistry


class PermissionEngine:
    """Checks and enforces agent permissions."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    async def check(
        self,
        agent_id: str,
        resource: str,
        operation: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PermissionEffect:
        """Check if an agent has permission. Logs the check."""
        policy = await self.registry.get_agent(agent_id)
        if not policy:
            effect = PermissionEffect.DENY
        else:
            effect = policy.check_permission(resource, operation)

        # Log the check
        entry = AuditEntry(
            agent_id=agent_id,
            agent_name=policy.agent_name if policy else "unknown",
            resource=resource,
            operation=operation,
            effect=effect,
            metadata=metadata or {},
        )
        await self.registry.log_audit(entry)

        return effect

    async def assert_allowed(
        self,
        agent_id: str,
        resource: str,
        operation: str | None = None,
    ) -> None:
        """Assert that an agent is allowed. Raises if denied."""
        effect = await self.check(agent_id, resource, operation)
        if effect == PermissionEffect.DENY:
            raise PermissionDeniedError(
                f"Agent {agent_id} denied access to {resource}"
                + (f" ({operation})" if operation else "")
            )

    async def request_escalation(
        self,
        agent_id: str,
        resource: str,
        reason: str,
    ) -> bool:
        """Request permission escalation."""
        policy = await self.registry.get_agent(agent_id)
        if not policy or not policy.escalation.enabled:
            return False

        # Log the escalation request
        entry = AuditEntry(
            agent_id=agent_id,
            agent_name=policy.agent_name,
            resource=resource,
            operation="escalation_request",
            effect=PermissionEffect.DENY,
            metadata={"reason": reason, "approver": policy.escalation.approver},
        )
        await self.registry.log_audit(entry)

        # In MVP, escalation is logged but not auto-approved
        # V2 will implement approval workflow
        return False


class PermissionDeniedError(Exception):
    """Raised when an agent is denied permission."""
    pass
