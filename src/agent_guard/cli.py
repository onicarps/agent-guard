"""CLI for agent-guard."""
from __future__ import annotations

import asyncio
import builtins

import typer
from rich.console import Console
from rich.table import Table

from .engine import PermissionEngine
from .policies import AgentPolicy, PermissionEffect
from .registry import AgentRegistry


def _substitute_placeholders(data: dict, name: str, top_level: bool = True) -> dict:
    """Recursively substitute {{name}} placeholders in policy data."""
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

app = typer.Typer(help="Agent-Guard: IAM for AI agents")
console = Console()


async def get_registry() -> AgentRegistry:
    """Get connected registry."""
    registry = AgentRegistry()
    await registry.connect()
    return registry


@app.command()
def register(
    name: str = typer.Option(..., help="Agent name"),
    role: str = typer.Option("default", help="Agent role"),
    policy_file: str | None = typer.Option(None, help="Policy YAML file"),
) -> None:
    """Register a new agent."""
    async def _run():
        registry = await get_registry()
        try:
            if policy_file:
                import yaml
                with open(policy_file) as f:
                    data = yaml.safe_load(f)
                # Substitute {{name}} placeholders and override agent_name
                data = _substitute_placeholders(data, name)
                policy = AgentPolicy(**data)
            else:
                policy = AgentPolicy(agent_name=name, role=role)

            agent_id = await registry.register_agent(policy)
            console.print(f"[green]✓[/green] Registered agent: {name} ({agent_id[:8]}...)")
        finally:
            await registry.close()

    asyncio.run(_run())


@app.command()
def check(
    agent_id: str = typer.Option(..., help="Agent ID"),
    resource: str = typer.Option(..., help="Resource name"),
    operation: str | None = typer.Option(None, help="Operation"),
) -> None:
    """Check if an agent has permission."""
    async def _run():
        registry = await get_registry()
        try:
            engine = PermissionEngine(registry)
            effect = await engine.check(agent_id, resource, operation)
            color = "green" if effect == PermissionEffect.ALLOW else "red"
            console.print(f"[{color}]{effect.value.upper()}[/{color}] {agent_id[:8]}... → {resource}" + (f" ({operation})" if operation else ""))
        finally:
            await registry.close()

    asyncio.run(_run())


@app.command(name="list")
def list_agents() -> None:
    """List all registered agents."""
    async def _run():
        registry = await get_registry()
        try:
            agents = await registry.list_agents()
            if not agents:
                console.print("No agents registered.")
                return

            table = Table(title="Registered Agents")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Role", style="yellow")
            table.add_column("Created", style="dim")

            for agent in agents:
                table.add_row(
                    agent["agent_id"][:8] + "...",
                    agent["agent_name"],
                    agent["role"],
                    str(agent["created_at"]),
                )
            console.print(table)
        finally:
            await registry.close()

    asyncio.run(_run())


@app.command()
def audit(
    agent_id: str | None = typer.Option(None, help="Filter by agent ID"),
    limit: int = typer.Option(20, help="Number of entries"),
) -> None:
    """View audit log."""
    async def _run():
        registry = await get_registry()
        try:
            entries = await registry.get_audit_log(agent_id, limit)
            if not entries:
                console.print("No audit entries.")
                return

            table = Table(title="Audit Log")
            table.add_column("Time", style="dim")
            table.add_column("Agent", style="cyan")
            table.add_column("Resource", style="green")
            table.add_column("Effect", style="bold")

            for entry in entries:
                color = "green" if entry["effect"] == "allow" else "red"
                table.add_row(
                    str(entry["timestamp"]),
                    entry["agent_name"],
                    entry["resource"],
                    f"[{color}]{entry['effect'].upper()}[/{color}]",
                )
            console.print(table)
        finally:
            await registry.close()

    asyncio.run(_run())


if __name__ == "__main__":
    app()
