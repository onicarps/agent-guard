"""Agent registry — stores and manages agent identities and policies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

from .policies import AgentPolicy, AuditEntry, PermissionEffect, ResourcePermission


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    role TEXT DEFAULT 'default',
    policy_json TEXT NOT NULL,
    parent_agent_id TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    entry_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    resource TEXT NOT NULL,
    operation TEXT,
    effect TEXT NOT NULL,
    timestamp REAL NOT NULL,
    metadata_json TEXT DEFAULT '{}',
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
"""


class AgentRegistry:
    """SQLite-backed agent registry."""

    def __init__(self, db_path: str = "agent_guard.db"):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Initialize database connection and schema."""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(DB_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def register_agent(self, policy: AgentPolicy) -> str:
        """Register a new agent with a policy. Returns agent_id."""
        import time
        now = time.time()
        await self._db.execute(
            "INSERT INTO agents (agent_id, agent_name, role, policy_json, parent_agent_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (policy.agent_id, policy.agent_name, policy.role, policy.model_dump_json(), policy.parent_agent_id, now, now)
        )
        await self._db.commit()
        return policy.agent_id

    async def get_agent(self, agent_id: str) -> AgentPolicy | None:
        """Get agent policy by ID."""
        cursor = await self._db.execute("SELECT policy_json FROM agents WHERE agent_id = ?", (agent_id,))
        row = await cursor.fetchone()
        if row:
            return AgentPolicy.model_validate_json(row["policy_json"])
        return None

    async def get_agent_by_name(self, agent_name: str) -> AgentPolicy | None:
        """Get agent policy by name."""
        cursor = await self._db.execute("SELECT policy_json FROM agents WHERE agent_name = ?", (agent_name,))
        row = await cursor.fetchone()
        if row:
            return AgentPolicy.model_validate_json(row["policy_json"])
        return None

    async def update_policy(self, agent_id: str, policy: AgentPolicy) -> bool:
        """Update an agent's policy."""
        import time
        cursor = await self._db.execute(
            "UPDATE agents SET policy_json = ?, role = ?, updated_at = ? WHERE agent_id = ?",
            (policy.model_dump_json(), policy.role, time.time(), agent_id)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        cursor = await self._db.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        cursor = await self._db.execute("SELECT agent_id, agent_name, role, created_at FROM agents")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def check_permission(self, agent_id: str, resource: str, operation: str | None = None) -> PermissionEffect:
        """Check if an agent has permission for a resource."""
        policy = await self.get_agent(agent_id)
        if not policy:
            return PermissionEffect.DENY
        inherited = await self.resolve_permissions(agent_id, _skip_self=True)
        return policy.check_permission(resource, operation, inherited)

    async def resolve_permissions(
        self,
        agent_id: str,
        _skip_self: bool = False,
    ) -> list[ResourcePermission]:
        """Walk the parent chain and collect inherited permissions.

        Returns merged list ordered from most-specific (self) to least-specific
        (root ancestor). Cycles are broken via a visited set, and missing
        ancestors are skipped silently.
        """
        merged: list[ResourcePermission] = []
        visited: set[str] = set()
        current_id: str | None = agent_id
        first = True
        while current_id and current_id not in visited:
            visited.add(current_id)
            policy = await self.get_agent(current_id)
            if not policy:
                break
            if not (first and _skip_self):
                merged.extend(policy.permissions)
            first = False
            current_id = policy.parent_agent_id
        return merged

    async def log_audit(self, entry: AuditEntry) -> None:
        """Write an audit log entry."""
        await self._db.execute(
            "INSERT INTO audit_log (entry_id, agent_id, agent_name, resource, operation, effect, timestamp, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (entry.entry_id, entry.agent_id, entry.agent_name, entry.resource, entry.operation, entry.effect.value, entry.timestamp, json.dumps(entry.metadata))
        )
        await self._db.commit()

    async def get_audit_log(self, agent_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Get audit log entries, optionally filtered by agent."""
        if agent_id:
            cursor = await self._db.execute(
                "SELECT * FROM audit_log WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?",
                (agent_id, limit)
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
