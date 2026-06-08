"""Tests for SHA-256 chained audit log (ONI-79)."""
from __future__ import annotations

import os
import tempfile

import pytest
import pytest_asyncio

from agent_guard.policies import AuditEntry, PermissionEffect
from agent_guard.registry import AgentRegistry


@pytest_asyncio.fixture
async def registry():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    reg = AgentRegistry(db_path)
    await reg.connect()
    yield reg
    await reg.close()
    os.unlink(db_path)


class TestAuditChain:
    @pytest.mark.asyncio
    async def test_chain_hash_stored(self, registry):
        entry = AuditEntry(
            agent_id="a1",
            agent_name="test",
            resource="res1",
            effect=PermissionEffect.ALLOW,
        )
        await registry.log_audit(entry)
        logs = await registry.get_audit_log(limit=1)
        assert len(logs) == 1
        assert logs[0]["chain_hash"] != ""
        assert len(logs[0]["chain_hash"]) == 64  # SHA-256 hex length

    @pytest.mark.asyncio
    async def test_chain_links_two_entries(self, registry):
        e1 = AuditEntry(
            agent_id="a1", agent_name="test", resource="r1", effect=PermissionEffect.ALLOW
        )
        await registry.log_audit(e1)

        e2 = AuditEntry(
            agent_id="a1", agent_name="test", resource="r2", effect=PermissionEffect.DENY
        )
        await registry.log_audit(e2)

        logs = await registry.get_audit_log(limit=10)
        # get_audit_log returns DESC order, so logs[0] is newest
        newest = logs[0]
        oldest = logs[1]
        assert newest["previous_hash"] == oldest["chain_hash"]
        assert oldest["previous_hash"] == ""

    @pytest.mark.asyncio
    async def test_chain_verify_valid(self, registry):
        for i in range(5):
            entry = AuditEntry(
                agent_id="a1",
                agent_name="test",
                resource=f"r{i}",
                effect=PermissionEffect.ALLOW,
            )
            await registry.log_audit(entry)

        assert await registry.verify_chain() is True

    @pytest.mark.asyncio
    async def test_chain_verify_tampered(self, registry):
        for i in range(3):
            entry = AuditEntry(
                agent_id="a1",
                agent_name="test",
                resource=f"r{i}",
                effect=PermissionEffect.ALLOW,
            )
            await registry.log_audit(entry)

        # Tamper with an entry's chain_hash directly in the DB
        await registry._db.execute(
            "UPDATE audit_log SET chain_hash = 'tampered' WHERE rowid = 2"
        )
        await registry._db.commit()

        assert await registry.verify_chain() is False

    @pytest.mark.asyncio
    async def test_chain_genesis_entry(self, registry):
        entry = AuditEntry(
            agent_id="a1",
            agent_name="test",
            resource="r1",
            effect=PermissionEffect.ALLOW,
        )
        await registry.log_audit(entry)
        logs = await registry.get_audit_log(limit=1)
        assert logs[0]["previous_hash"] == ""

    @pytest.mark.asyncio
    async def test_chain_multiple_entries(self, registry):
        entries = []
        for i in range(5):
            entry = AuditEntry(
                agent_id="a1",
                agent_name="test",
                resource=f"r{i}",
                effect=PermissionEffect.ALLOW,
            )
            await registry.log_audit(entry)
            entries.append(entry)

        assert await registry.verify_chain() is True

        logs = await registry.get_audit_log(limit=10)
        # DESC order: newest first
        for i in range(len(logs) - 1):
            assert logs[i]["previous_hash"] == logs[i + 1]["chain_hash"]
