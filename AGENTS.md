# Agent-Guard — Project Context for AI Agents

## Mission

**Agent-Guard is "IAM for AI Agents"** — a permission and access control framework that gives developers fine-grained control over what their AI agents can do.

## Tech Stack

- Python 3.11+, Pydantic v2, SQLite (aiosqlite), Typer + Rich, httpx (async)
- pytest + pytest-asyncio for testing
- Black + isort + mypy + ruff

## File Organization

```
workspace/
├── pyproject.toml
├── README.md
├── src/agent_guard/
│   ├── __init__.py
│   ├── policies.py      # Pydantic models: AgentPolicy, ResourcePermission, AuditEntry, etc.
│   ├── registry.py      # SQLite-backed agent registry (AgentRegistry)
│   ├── engine.py        # PermissionEngine: check, assert_allowed, request_escalation
│   ├── middleware.py    # GuardMiddleware: guard_tool, guarded decorator
│   ├── cli.py           # CLI: register, check, list, audit commands
│   └── integrations/
│       ├── langchain.py # LangChainGuard + create_guarded_agent
│       ├── crewai.py    # CrewAIGuard
│       └── custom.py    # @guarded decorator
├── tests/
│   ├── test_core.py              # Existing tests for policies, registry, engine
│   ├── test_cli.py               # CLI tests (TO BE WRITTEN)
│   ├── test_middleware.py        # Middleware tests (TO BE WRITTEN)
│   ├── test_engine.py            # Engine escalation tests (TO BE WRITTEN)
│   ├── test_registry.py          # Registry edge cases (TO BE WRITTEN)
│   └── integrations/
│       ├── test_custom.py        # Existing @guarded decorator tests
│       ├── test_langchain.py     # LangChain integration tests (TO BE WRITTEN)
│       └── test_crewai.py        # CrewAI integration tests (TO BE WRITTEN)
└── templates/
    ├── read_only.yaml
    ├── developer.yaml
    └── admin.yaml
```

## Build Rules

1. **Test-driven.** Write tests before code. Minimum 80% coverage.
2. **Small commits.** One feature per commit. Clear commit messages.
3. **Type hints everywhere.** No `any` types. Pydantic models for all data.
4. **Async by default.** Use `httpx` for HTTP, `aiosqlite` for DB.
5. **Error handling.** Every function has proper error handling. No silent failures.

## Database Schema

```sql
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
```

## Testing

- Run tests: `.venv/bin/python -m pytest -xvs`
- Run with coverage: `.venv/bin/python -m pytest --cov=src --cov-report=term-missing`
- All tests must pass before merging
- Use `tempfile.NamedTemporaryFile(suffix=".db", delete=False)` for test DBs
- Use `pytest_asyncio.fixture` for async fixtures
- Clean up temp DBs with `os.unlink(db_path)` in fixture teardown

## Code Style
- Black formatting (line-length 100)
- isort imports
- mypy strict mode
- ruff linting

## Commit Convention
- Format: `feat: description`, `fix: description`, `test: description`
- Reference Linear issues when available: `test: add CLI tests (ONI-74)`
