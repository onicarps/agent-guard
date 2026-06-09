"""Permission engine — enforces agent permissions."""
from __future__ import annotations

from typing import Any

from .policies import AuditEntry, PermissionEffect, ResourcePermission
from .rate_limiter import RateLimiter
from .registry import AgentRegistry


class PermissionEngine:
    """Checks and enforces agent permissions."""

    def __init__(self, registry: AgentRegistry, rate_limiter: RateLimiter | None = None):
        self.registry = registry
        self.rate_limiter = rate_limiter or RateLimiter()

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
            inherited = await self.registry.resolve_permissions(agent_id, _skip_self=True)
            effect = policy.check_permission(resource, operation, inherited)

            if effect == PermissionEffect.ALLOW:
                matching = _find_allow_permission(policy.permissions, resource)
                if matching is None:
                    matching = _find_allow_permission(inherited, resource)
                if matching is not None:
                    constraints = matching.constraints
                    if constraints.max_per_hour is not None or constraints.max_per_day is not None:
                        if not await self.rate_limiter.check(
                            agent_id,
                            resource,
                            max_per_hour=constraints.max_per_hour,
                            max_per_day=constraints.max_per_day,
                        ):
                            effect = PermissionEffect.DENY
                            metadata = {**(metadata or {}), "rate_limited": True}

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


def _find_allow_permission(
    permissions: list[ResourcePermission],
    resource: str,
) -> ResourcePermission | None:
    for perm in permissions:
        if perm.name == resource and perm.effect == PermissionEffect.ALLOW:
            return perm
    return None
