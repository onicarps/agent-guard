# Agent-Guard v0.1.0 — Security Model

## Threat Model

Agent-Guard is designed to mitigate the following threats in AI agent ecosystems:

### T1: Unauthorized Tool Execution
**Threat:** An AI agent calls a tool or API it should not have access to, either due to prompt injection, misconfiguration, or emergent behavior.

**Mitigation:** Permission checks are enforced at the middleware/integration layer. Every tool call is checked against the agent's policy before execution. If no matching `ALLOW` rule exists, the call is denied. This is fail-closed by default.

### T2: Privilege Escalation
**Threat:** An agent gains broader permissions than intended, either by modifying its own policy or by exploiting a flaw in the permission system.

**Mitigation:** Policies are stored in an external SQLite database, not in the agent's context window. Agents cannot modify their own policies through normal tool calls — policy changes require CLI access. Permission inheritance follows a strict parent-child chain with cycle detection to prevent loops.

### T3: Audit Log Tampering
**Threat:** An attacker (or rogue agent) modifies or deletes audit log entries to cover up unauthorized actions.

**Mitigation:** Every audit entry includes a SHA-256 chain hash. Each entry's hash is computed over its own fields plus the previous entry's hash. This creates a tamper-evident chain — modifying any entry breaks the chain from that point forward. The `verify_chain()` method can detect any modification or deletion.

### T4: Rate Limit Bypass
**Threat:** An agent makes an excessive number of calls to a resource, potentially causing denial of service or excessive costs.

**Mitigation:** Per-agent, per-resource sliding window rate limits. Two independent windows (hourly and daily) ensure both burst and sustained abuse are caught. Rate limits are enforced atomically with permission checks — a rate-limited call returns DENY and is logged with a `rate_limited` metadata flag.

### T5: Circular Permission Inheritance
**Threat:** Two or more agents reference each other as parents, creating an infinite loop that could crash the system or cause denial of service.

**Mitigation:** The `resolve_permissions()` method tracks visited agent IDs in a set. If a cycle is detected (an agent is visited twice), the traversal stops at that point. The chain walked so far is still valid.

## Permission Model

### Design Principles

1. **Fail-closed:** If no policy exists for an agent, or no rule matches a resource, the result is DENY. There are no implicit allows.
2. **Deny precedence:** Explicit DENY rules always take precedence over ALLOW rules for the same resource, at the same inheritance level.
3. **Child overwrites child:** A child agent's permissions override inherited permissions from parents.
4. **Least privilege:** Templates start restrictive (read_only) and require explicit escalation for broader access.

### Permission Resolution Order

When checking if agent X can perform operation Y on resource Z:

1. Check X's own DENY rules for Z → if found, DENY
2. Check X's own ALLOW rules for Z → if found (and operation matches constraints), ALLOW
3. Walk up the parent chain (X → parent → grandparent → ...):
   a. Check parent's DENY rules for Z → if found, DENY
   b. Check parent's ALLOW rules for Z → if found, ALLOW
4. If nothing matched → DENY (default deny)

### Inheritance Rules

| Scenario | Result |
|----------|--------|
| Parent allows, child has no rule | Child inherits ALLOW |
| Parent allows, child denies | Child DENY wins |
| Parent denies, child allows | Child ALLOW wins |
| Both allow, child has stricter constraints | Child's constraints apply |
| Circular parent reference | Cycle broken, chain walked so far is used |
| Missing/deleted parent | Chain stops at missing agent |

### Resource Types

| Type | Description | Example Resources |
|------|-------------|-------------------|
| `tool` | Generic tool calls | `search`, `calculator` |
| `api` | External API access | `deploy`, `github`, `api-call` |
| `database` | Database operations | `database`, `cache` |
| `file` | File system access | `file_system` |
| `email` | Email sending | `send_email`, `email` |
| `payment` | Financial transactions | `charge_card`, `payment` |

## Audit Trail

### What Is Logged

Every permission check (allow or deny) creates an audit entry with:
- `entry_id` — UUID v4
- `agent_id` — the agent that was checked
- `agent_name` — human-readable name
- `resource` — the resource that was checked
- `operation` — the operation (read, write, delete) or None
- `effect` — ALLOW or DENY
- `timestamp` — Unix epoch time
- `metadata` — additional context (e.g., `{"rate_limited": true}`, `{"reason": "..."}`)
- `previous_hash` — chain hash of the previous entry (genesis entry: "")
- `chain_hash` — SHA-256 of all entry fields + previous_hash

### Chain Hash Computation

```
chain_hash = SHA256(
    entry_id + agent_id + resource + operation + effect
    + str(timestamp) + metadata_json + previous_hash
)
```

This means:
- **Modifying any field** of an entry changes its chain hash, breaking the link to the next entry.
- **Deleting an entry** breaks the chain because the next entry's `previous_hash` no longer matches.
- **Inserting a forged entry** requires recomputing all subsequent chain hashes.

### Verification

```python
is_intact = await registry.verify_chain()
```

`verify_chain()` iterates through all entries in chronological order, recomputing each entry's chain hash and verifying:
1. `entry.previous_hash == previous_entry.chain_hash` (chain is unbroken)
2. `recomputed_hash == entry.chain_hash` (entry data is unmodified)

Returns `True` if the entire chain is intact, `False` if any tampering is detected.

### Limitations

- **In-memory rate limiter state is not persisted.** If the process restarts, rate limit counters reset. For multi-process deployments, use a shared rate limiting backend (Redis, database).
- **SQLite is single-writer.** High-concurrency deployments should consider PostgreSQL.
- **Chain hashes detect tampering but don't prevent it.** The database should have appropriate filesystem permissions. For high-assecurity deployments, consider append-only storage or external audit log shipping.
- **Escalation requests are logged but not auto-approved (MVP).** V2 will implement an approval workflow with notifications.

## Data Storage Security

- The SQLite database file should have restricted filesystem permissions (`chmod 600`).
- The `.env` file containing API keys is gitignored — never commit secrets.
- The `agent-guard` CLI reads database paths from code, not from user input, preventing path traversal.
- All Pydantic models enforce type validation — malformed YAML policies will fail at registration, not at permission check time.

## Deployment Recommendations

1. **Use a dedicated database path** outside the application directory for production.
2. **Run with least privilege** — the agent process only needs read/write access to the database file.
3. **Monitor the audit log** — set up alerts for DENY patterns that might indicate prompt injection attempts.
4. **Review policies regularly** — use `agent-guard audit` to review recent permission decisions.
5. **Back up the database** — the audit chain can only be verified if all entries are preserved.
6. **For production**, consider running the rate limiter with a persistent backend instead of in-memory.

## Reporting Security Vulnerabilities

If you find a security vulnerability in Agent-Guard, please report it responsibly. The project is MIT licensed and maintained by the ONI team.
