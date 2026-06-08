# Factory Mission 2: Missing Features (Phase 3)

## Project Context

Agent-Guard is an "IAM for AI Agents" Python library. Workspace: `/home/oni/.hermes/profiles/agent-guard/workspace/`

Current state: 53 tests pass, 99% coverage. Now implementing the 3 missing features.

## Your Mission

Implement 3 missing features. Follow TDD: write failing test → implement → test passes → commit.

### Feature 1: Permission Inheritance (ONI-77)

**Current state**: `parent_agent_id` field exists on `AgentPolicy` (policies.py line 57) and in the DB schema (registry.py line 19), but `check_permission()` never reads it.

**What to implement**:

1. Add a method `resolve_permissions(agent_id: str) -> list[ResourcePermission]` to `AgentRegistry` that:
   - Gets the agent's policy
   - If `parent_agent_id` is set, recursively collects parent permissions
   - Uses a `visited` set to prevent infinite loops from circular inheritance
   - Returns merged list: child permissions + parent permissions (child wins on conflict)

2. Modify `AgentPolicy.check_permission()` to accept an optional `inherited_permissions: list[ResourcePermission] = None` parameter
   - Check own permissions first (deny takes precedence)
   - If not found in own permissions, check inherited permissions
   - Default deny if not found in either

3. Modify `PermissionEngine.check()` to:
   - Call `registry.resolve_permissions(agent_id)` to get inherited permissions
   - Pass inherited permissions to `policy.check_permission()`

4. Add tests in `tests/test_inheritance.py`:
   - `test_inheritance_basic`: child inherits parent's permissions
   - `test_inheritance_child_override`: child's deny overrides parent's allow
   - `test_inheritance_chain`: grandchild → child → parent chain
   - `test_inheritance_circular`: circular reference doesn't infinite loop
   - `test_inheritance_no_parent`: agent without parent works normally
   - `test_inheritance_parent_not_found`: missing parent doesn't crash

### Feature 2: Rate Limiting Enforcement (ONI-78)

**Current state**: `ToolConstraint` model has `max_per_hour` and `max_per_day` fields that are never checked.

**What to implement**:

1. Create a new file `src/agent_guard/rate_limiter.py`:
   ```python
   class RateLimiter:
       """Sliding window rate limiter, per-agent per-resource."""
       
       def __init__(self):
           self._windows: dict[tuple[str, str], list[float]] = {}
       
       def check(self, agent_id: str, resource: str, max_per_hour: int | None = None, max_per_day: int | None = None) -> bool:
           """Returns True if within rate limit, False if exceeded."""
           # Sliding window: count entries within the time window
           # Clean up old entries outside the window
           # Return True if count < max, False otherwise
           # Record the current timestamp if allowed
   ```

   Key requirements:
   - Use `time.time()` for timestamps
   - Sliding window: for `max_per_hour`, count entries within last 3600 seconds; for `max_per_day`, count within last 86400 seconds
   - Store timestamps in a dict keyed by `(agent_id, resource)`
   - Clean up old entries on each check
   - Record the current timestamp when allowing (before returning True)
   - Do NOT use `time.sleep()` — just return False when limit exceeded

2. Integrate into `PermissionEngine.check()`:
   - After permission check passes (effect == ALLOW), check rate limits
   - Get `max_per_hour` and `max_per_day` from the matching `ResourcePermission.constraints`
   - If rate limit exceeded, log a DENY audit entry and return DENY
   - If no constraints set, skip rate limiting

3. Add tests in `tests/test_rate_limiter.py`:
   - `test_rate_limiter_allows_within_limit`: 5 calls with max_per_hour=10 → all allowed
   - `test_rate_limiter_denies_over_limit`: 11 calls with max_per_hour=10 → 11th denied
   - `test_rate_limiter_sliding_window`: calls spread over time, old ones expire
   - `test_rate_limiter_per_agent_isolated`: agent A and B have separate counters
   - `test_rate_limiter_per_resource_isolated`: different resources have separate counters
   - `test_rate_limiter_no_constraints`: no max_per_hour/day → always allowed
   - `test_rate_limiter_day_window`: max_per_day enforcement
   - `test_engine_integration_rate_limit`: PermissionEngine.check() denies when rate limited

### Feature 3: Audit Log Hash Chain (ONI-79)

**Current state**: Audit entries are stored in SQLite with no hash chain.

**What to implement**:

1. Add a `previous_hash` column to the audit_log table via a migration approach:
   - In `AgentRegistry.connect()`, after creating tables, run:
     ```sql
     ALTER TABLE audit_log ADD COLUMN previous_hash TEXT DEFAULT ''
     ```
   - Use `ALTER TABLE IF NOT EXISTS` pattern (SQLite doesn't support IF NOT EXISTS for ALTER, so catch the error)

2. Modify `AuditEntry` model to include `previous_hash: str = ""`

3. Modify `AgentRegistry.log_audit()`:
   - Before inserting, query the most recent audit entry's hash: `SELECT entry_id FROM audit_log ORDER BY timestamp DESC LIMIT 1`
   - Compute chain hash: `SHA256(entry_id + agent_id + resource + operation + effect + str(timestamp) + metadata_json + previous_entry_hash)`
   - Store the computed hash in a new `chain_hash` column
   - Store the previous entry's hash in `previous_hash`

4. Add a method `verify_chain() -> bool` to `AgentRegistry`:
   - Iterate through audit entries in timestamp order
   - Recompute each entry's chain_hash
   - Verify it matches the stored chain_hash
   - Verify each entry's previous_hash matches the prior entry's chain_hash
   - Return True if chain is intact, False if tampered

5. Add tests in `tests/test_audit_chain.py`:
   - `test_chain_hash_stored`: after logging entry, chain_hash is not empty
   - `test_chain_links_two_entries`: second entry's previous_hash == first entry's chain_hash
   - `test_chain_verify_valid`: verify_chain() returns True for valid chain
   - `test_chain_verify_tampered`: verify_chain() returns False if entry modified
   - `test_chain_genesis_entry`: first entry has previous_hash = '' or sentinel
   - `test_chain_multiple_entries`: 5 entries all linked correctly

## Commit Strategy

Commit after each feature:
1. `feat: permission inheritance with cycle detection (ONI-77)`
2. `feat: sliding window rate limiting enforcement (ONI-78)`
3. `feat: SHA-256 chained audit log with tamper detection (ONI-79)`

## Verification

After all 3 features:
```bash
.venv/bin/python -m pytest --cov=src --cov-report=term-missing
```

Target: maintain 95%+ coverage (new features should have tests).

## Important Notes

- Do NOT modify existing tests — only add new test files
- Do NOT break existing functionality — all 53 existing tests must still pass
- Use the existing code patterns and style
- The `guard_tool` method in middleware.py does NOT pass metadata to assert_allowed — this is intentional (fixed in previous commit)
