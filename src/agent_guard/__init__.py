"""Agent-Guard: IAM for AI agents."""
__version__ = "0.1.1"

from .policies import AgentPolicy, PermissionEffect, ResourcePermission, ResourceType
from .registry import AgentRegistry
from .engine import PermissionEngine, PermissionDeniedError
from .middleware import GuardMiddleware
from .templates import register_from_template

__all__ = [
    "AgentPolicy",
    "PermissionEffect",
    "ResourcePermission",
    "ResourceType",
    "AgentRegistry",
    "PermissionEngine",
    "PermissionDeniedError",
    "GuardMiddleware",
    "register_from_template",
]
