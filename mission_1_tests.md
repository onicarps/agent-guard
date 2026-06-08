# Factory Mission 1: Test Coverage 80%+ and Bug Fixes

## Project Context

Agent-Guard is an "IAM for AI Agents" Python library. Workspace: `/home/oni/.hermes/profiles/agent-guard/workspace/`

Current state: 14/14 tests pass, 60% coverage. Target: 80%+.

## Critical Bug Fixes Already Applied (do NOT re-fix)

1. middleware.py: removed `metadata` kwarg from `assert_allowed()` call — was causing TypeError
2. langchain.py: moved `import asyncio` to top of file — was used before import

## Your Mission

Write ALL missing tests. Follow TDD: write the test first, verify it passes. Use the existing test patterns (pytest, pytest-asyncio, tempfile for DB fixtures).

### Test File Structure

Create these test files:
1. `tests/test_cli.py` — CLI tests (currently 0% coverage, 82 lines)
2. `tests/test_middleware.py` — Middleware tests (currently 47% coverage)
3. `tests/test_engine.py` — Engine escalation tests (request_escalation enabled/disabled)
4. `tests/test_registry.py` — Registry edge cases (update_policy, delete_agent, get_agent_by_name)
5. `tests/integrations/test_langchain.py` — LangChain integration tests (currently 0%)
6. `tests/integrations/test_crewai.py` — CrewAI integration tests (currently 0%)

### Detailed Test Requirements

#### 1. tests/test_cli.py — CLI Tests

Test all 4 CLI commands using `typer.testing.CliRunner`:

- `test_register_with_name_only`: register agent with just a name, verify output contains "Registered agent"
- `test_register_with_policy_file`: register using a YAML policy file (create a temp YAML from templates/read_only.yaml format)
- `test_register_invalid_yaml`: register with malformed YAML, verify error handling
- `test_check_allow`: register agent with permission, check permission → ALLOW
- `test_check_deny`: register agent without permission, check permission → DENY
- `test_check_unknown_agent`: check permission for non-existent agent → DENY
- `test_list_empty`: list when no agents registered → "No agents registered"
- `test_list_with_agents`: register 2 agents, list → table with 2 rows
- `test_audit_empty`: audit with no entries → "No audit entries"
- `test_audit_with_entries`: create agent, check permission, audit → shows entry

Use `CliRunner` from typer.testing. Invoke commands and assert on output and exit_code.

#### 2. tests/test_middleware.py — Middleware Tests

Test `GuardMiddleware` class:

- `test_guard_tool_allows`: create agent with permission, call guard_tool → no exception
- `test_guard_tool_denies`: create agent without permission, call guard_tool → raises PermissionDeniedError
- `test_guarded_decorator_async`: decorate async function with @guarded, verify it runs when allowed
- `test_guarded_decorator_async_denies`: decorate async function, verify PermissionDeniedError when denied
- `test_guarded_decorator_sync`: decorate sync function with @guarded, verify it runs when allowed
- `test_guarded_decorator_sync_denies`: decorate sync function, verify PermissionDeniedError when denied

Use the same fixture pattern as test_core.py (tempfile DB, AgentRegistry, PermissionEngine).

#### 3. tests/test_engine.py — Engine Escalation Tests

Test `PermissionEngine.request_escalation()`:

- `test_escalation_disabled_by_default`: agent with no escalation config → request_escalation returns False
- `test_escalation_enabled_but_not_auto_approved`: agent with escalation.enabled=True → request_escalation returns False (logs the request)
- `test_escalation_logs_audit_entry`: after request_escalation, audit log contains escalation_request entry
- `test_escalation_with_nonexistent_agent`: request_escalation for unknown agent → returns False

#### 4. tests/test_registry.py — Registry Edge Cases

Test methods that exist but are untested:

- `test_get_agent_by_name`: register agent, retrieve by name → correct policy
- `test_get_agent_by_name_not_found`: get by non-existent name → None
- `test_update_policy`: register agent, update policy, retrieve → updated policy
- `test_update_policy_not_found`: update non-existent agent → returns False
- `test_delete_agent`: register agent, delete, retrieve → None
- `test_delete_agent_not_found`: delete non-existent agent → returns False
- `test_get_audit_log_by_agent`: create 2 agents, log entries for both, filter by agent_id → only that agent's entries
- `test_get_audit_log_limit`: create 5 entries, query with limit=3 → returns 3

#### 5. tests/integrations/test_langchain.py — LangChain Integration Tests

Test `LangChainGuard` and `create_guarded_agent`:

- `test_guard_tool_allows`: wrap async tool with guard, call when allowed → returns result
- `test_guard_tool_denies`: wrap async tool with guard, call when denied → PermissionDeniedError
- `test_guard_tool_sync_allows`: wrap sync tool with guard, call when allowed → returns result
- `test_guard_tool_sync_denies`: wrap sync tool with guard, call when denied → PermissionDeniedError
- `test_create_guarded_agent_mixed`: create list with async + sync tools, verify all are guarded
- `test_create_guarded_agent_all_async`: create list with only async tools
- `test_guarded_tool_preserves_name`: wrapped function has same __name__ as original

#### 6. tests/integrations/test_crewai.py — CrewAI Integration Tests

Test `CrewAIGuard`:

- `test_guard_task_allows`: wrap async task with guard, call when allowed → returns result
- `test_guard_task_denies`: wrap async task with guard, call when denied → PermissionDeniedError
- `test_guard_task_sync_allows`: wrap sync task with guard, call when allowed → returns result
- `test_guard_task_sync_denies`: wrap sync task with guard, call when denied → PermissionDeniedError
- `test_guarded_task_preserves_name`: wrapped function has same __name__ as original

### Fixtures

Use the same pattern as test_core.py:
```python
@pytest_asyncio.fixture
async def engine():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    reg = AgentRegistry(db_path)
    await reg.connect()
    eng = PermissionEngine(reg)
    yield eng, reg, db_path
    await reg.close()
    os.unlink(db_path)
```

### Verification

After writing all tests, run:
```bash
.venv/bin/python -m pytest --cov=src --cov-report=term-missing
```

Target: 80%+ overall coverage. CLI should go from 0% to 100%. Middleware from 47% to 100%. LangChain and CrewAI from 0% to 90%+.

### Commit

After all tests pass:
```bash
git add -A
git commit -m "test: add CLI, middleware, engine escalation, registry edge case, and integration tests (ONI-74, ONI-75, ONI-76)"
```

## Important Notes

- Do NOT modify source code (policies.py, engine.py, registry.py, middleware.py, cli.py, integrations/*.py) — only write tests
- Use the existing test patterns and fixtures from test_core.py and tests/integrations/test_custom.py
- If a test reveals a bug in the source code, document it but do NOT fix it — that's for Mission 2
- Run the full test suite after each test file to ensure nothing breaks
