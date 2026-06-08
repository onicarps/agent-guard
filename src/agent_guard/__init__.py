"""Agent-Guard: IAM for AI agents."""
__version__ = "0.1.0"

from .policies import AgentPolicy, PermissionEffect, ResourcePermission, ResourceType
from .registry import AgentRegistry
from .engine import PermissionEngine, PermissionDeniedError
from .middleware import GuardMiddleware

__all__ = [
    "AgentPolicy",
    "PermissionEffect",
    "ResourcePermission",
    "ResourceType",
    "AgentRegistry",
    "PermissionEngine",
    "PermissionDeniedError",
    "GuardMiddleware",
]
