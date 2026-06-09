"""Template helper functions for agent-guard."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

from .policies import AgentPolicy

TEMPLATES_DIR = Path(__file__).parent / "templates"


def register_from_template(name: str, template: str | Path, role: str = "default") -> AgentPolicy:
    """Load a YAML template, substitute placeholders, and return an AgentPolicy.
    
    Args:
        name: Agent name (substitutes {{name}} in template)
        template: Template name (e.g. "read_only.yaml") or Path to custom YAML file
        role: Optional role override. If not specified, uses the template's role.
    
    Returns:
        An AgentPolicy with all placeholders substituted.
    
    Example:
        >>> policy = register_from_template("my-agent", "read_only.yaml")
        >>> policy.agent_name
        'my-agent'
        >>> policy.role
        'read_only'
    """
    if isinstance(template, Path) or str(template).endswith((".yaml", ".yml")):
        if isinstance(template, str) and not template.endswith((".yaml", ".yml")):
            template_path = TEMPLATES_DIR / f"{template}.yaml"
        else:
            template_path = Path(template)
    else:
        template_path = TEMPLATES_DIR / template

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    with open(template_path) as f:
        data = yaml.safe_load(f)

    # Substitute {{name}} placeholders
    data = _substitute_placeholders(data, name)

    # Override role if specified
    if role != "default":
        data["role"] = role

    return AgentPolicy(**data)


def _substitute_placeholders(data: dict, name: str, top_level: bool = True) -> dict:
    """Recursively substitute {{name}} placeholders in policy data."""
    import builtins

    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = value.replace("{{name}}", name)
        elif isinstance(value, dict):
            result[key] = _substitute_placeholders(value, name, top_level=False)
        elif isinstance(value, builtins.list):
            result[key] = [
                v.replace("{{name}}", name) if isinstance(v, str)
                else _substitute_placeholders(v, name, top_level=False) if isinstance(v, dict)
                else v
                for v in value
            ]
        else:
            result[key] = value
    if top_level:
        result["agent_name"] = name
    return result
