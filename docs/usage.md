# Agent-Guard v0.1.0 — Usage Guide

## What Is Agent-Guard?

Agent-Guard is **IAM for AI Agents** — a Python library that gives developers fine-grained control over what their AI agents can do. Instead of asking "is this output good?" (subjective), Agent-Guard asks "is this agent allowed to do this?" (objective, enforceable).

**Core capabilities:**
- Register agents with YAML permission policies
- Check permissions before tool calls (allow/deny with audit logging)
- Enforce rate limits (sliding window, per-agent per-tool)
- Permission inheritance with cycle detection
- SHA-256 chained audit log with tamper detection
- LangChain and CrewAI integrations

## Installation

```bash
pip install agent-guard
```

For framework integrations:
```bash
pip install agent-guard[langchain]   # LangChain support
pip install agent-guard[crewai]      # CrewAI support
```

Requires Python 3.11+.

## Quick Start

### 1. Register an Agent

```bash
# Register with a YAML policy file
agent-guard register --name "my-agent" --policy-file templates/developer.yaml

# Register with defaults (no permissions)
agent-guard register --name "minimal-agent"
```

### 2. Check Permissions

```bash
agent-guard check --agent-id <agent-id> --resource "database" --operation "read"
# Output: ALLOW abc12345... → database (read)

agent-guard check --agent-id <agent-id> --resource "payment"
# Output: DENY abc12345... → payment
```

### 3. List Agents

```bash
agent-guard list
# ┏━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
# ┃ ID       ┃ Name         ┃ Role     ┃ Created             ┃
# ┡━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
# │ abc12345 │ my-agent     │ developer │ 1717831234.567      │
# └──────────┴──────────────┴──────────┴─────────────────────┘
```

### 4. View Audit Log

```bash
# All entries
agent-guard audit --limit 20

# Filtered by agent
agent-guard audit --agent-id <agent-id> --limit 10
```

## Policy Definitions

Policies are YAML files that define what an agent can and cannot do:

```yaml
agent_name: "my-agent"
role: "developer"
permissions:
  - name: "database"
    type: "database"
    effect: "allow"
    constraints:
      allowed_operations: ["read", "write"]
      allowed_tables: ["staging", "test"]
  - name: "deploy"
    type: "api"
    effect: "deny"
escalation:
  enabled: true
  approver: "tech-lead"
  max_escalations_per_day: 5
```

### Permission Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Resource identifier (e.g., "database", "deploy") |
| `type` | string | One of: `tool`, `api`, `database`, `file`, `email`, `payment` |
| `effect` | string | `allow` or `deny` |
| `constraints` | object | See below |

### Constraint Fields

| Field | Type | Description |
|-------|------|-------------|
| `allowed_operations` | list | `read`, `write`, `delete` |
| `allowed_tables` | list | Database table names |
| `allowed_domains` | list | URL domains for API calls |
| `max_per_hour` | int | Rate limit: max calls per hour |
| `max_per_day` | int | Rate limit: max calls per day |

### Pre-built Templates

| Template | Description |
|----------|-------------|
| `read_only.yaml` | Read-only access to DB and files. Denies email and payments. |
| `developer.yaml` | Read/write to staging, GitHub access. Denies deploy and payments. Escalation to tech-lead. |
| `admin.yaml` | Full access to all resource types. No escalation. |

### Permission Rules

1. **Explicit deny takes precedence** over allow for the same resource
2. **Default deny**: if no rule matches, access is denied
3. **Child permissions override parent** in inheritance chains
4. **Rate limits** are checked after permission is granted — exceeding the limit flips ALLOW to DENY

## Python API

### Basic Usage

```python
import asyncio
from agent_guard import AgentPolicy, AgentRegistry, PermissionEngine
from agent_guard.policies import ResourcePermission, ResourceType, PermissionEffect

async def main():
    registry = AgentRegistry("my-agents.db")
    await registry.connect()

    # Create a policy
    policy = AgentPolicy(
        agent_name="data-analyst",
        role="analyst",
        permissions=[
            ResourcePermission(
                name="database",
                type=ResourceType.DATABASE,
                effect=PermissionEffect.ALLOW,
                constraints={"allowed_operations": ["read"]}
            ),
            ResourcePermission(
                name="payment",
                type=ResourceType.PAYMENT,
                effect=PermissionEffect.DENY,
            ),
        ],
    )

    # Register the agent
    agent_id = await registry.register_agent(policy)

    # Check permissions
    engine = PermissionEngine(registry)
    effect = await engine.check(agent_id, "database", "read")
    print(effect)  # PermissionEffect.ALLOW

    effect = await engine.check(agent_id, "payment")
    print(effect)  # PermissionEffect.DENY

    await registry.close()

asyncio.run(main())
```

### Permission Inheritance

```python
# Parent agent with base permissions
parent_policy = AgentPolicy(
    agent_name="base-agent",
    permissions=[
        ResourcePermission(name="database", type=ResourceType.DATABASE, effect=PermissionEffect.ALLOW),
    ],
)
parent_id = await registry.register_agent(parent_policy)

# Child agent inherits from parent, adds own permissions
child_policy = AgentPolicy(
    agent_name="child-agent",
    parent_agent_id=parent_id,
    permissions=[
        ResourcePermission(name="deploy", type=ResourceType.API, effect=PermissionEffect.ALLOW),
        ResourcePermission(name="database", type=ResourceType.DATABASE, effect=PermissionEffect.DENY, 
                          constraints=ToolConstraint(allowed_operations=["write"])),
    ],
)
child_id = await registry.register_agent(child_policy)

# Child can deploy (own permission)
# Child can read database (inherited from parent, deny only applies to write)
# Child inherits parent's allows unless overridden
```

### Rate Limiting

```python
from agent_guard.policies import ToolConstraint

policy = AgentPolicy(
    agent_name="rate-limited-agent",
    permissions=[
        ResourcePermission(
            name="api-call",
            type=ResourceType.API,
            effect=PermissionEffect.ALLOW,
            constraints=ToolConstraint(max_per_hour=100, max_per_day=1000),
        ),
    ],
)
```

### Audit Log Verification

```python
# Verify the entire audit chain hasn't been tampered with
is_valid = await registry.verify_chain()
if not is_valid:
    print("WARNING: Audit log has been tampered with!")
```

## Framework Integrations

### LangChain

```python
from agent_guard.langchain import LangChainGuard, create_guarded_agent
from agent_guard import AgentRegistry, PermissionEngine
from langchain.tools import tool

registry = AgentRegistry()
await registry.connect()
engine = PermissionEngine(registry)

# Guard individual tools
guard = LangChainGuard(engine, agent_id)

@guard.guard_tool
@tool
async def search_db(query: str) -> str:
    return f"Results for: {query}"

# Or guard a list of tools at once
guarded_tools = create_guarded_agent(engine, agent_id, [tool1, tool2, tool3])
```

### CrewAI

```python
from agent_guard.crewai import CrewAIGuard

guard = CrewAIGuard(engine, agent_id)

@guard.guard_task
async def analyze_data(dataset: str) -> str:
    return f"Analysis of {dataset}"

@guard.guard_task_sync
def generate_report(analysis: str) -> str:
    return f"Report: {analysis}"
```

### Custom Decorator

```python
from agent_guard.integrations.custom import guarded

@guarded(engine, agent_id, "my-sensitive-tool")
async def sensitive_operation(data: str) -> str:
    # Only executes if agent has permission
    return process(data)
```

## CLI Reference

### `agent-guard register`

Register a new agent with a policy.

```
agent-guard register --name NAME [--role ROLE] [--policy-file FILE]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--name` | required | Agent name |
| `--role` | `default` | Agent role label |
| `--policy-file` | none | Path to YAML policy file |

### `agent-guard check`

Check if an agent has permission for a resource.

```
agent-guard check --agent-id ID --resource RESOURCE [--operation OP]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--agent-id` | required | Agent ID (from register) |
| `--resource` | required | Resource name |
| `--operation` | none | Operation: read, write, delete |

### `agent-guard list`

List all registered agents.

```
agent-guard list
```

### `agent-guard audit`

View the audit log.

```
agent-guard audit [--agent-id ID] [--limit N]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--agent-id` | none | Filter by agent ID |
| `--limit` | 20 | Number of entries |

## Architecture

```
agent_guard/
├── policies.py      # Data models (AgentPolicy, ResourcePermission, AuditEntry)
├── registry.py      # SQLite-backed agent registry + audit log
├── engine.py        # PermissionEngine (check, assert_allowed, request_escalation)
├── middleware.py    # GuardMiddleware (guard_tool, guarded decorator)
├── rate_limiter.py  # Sliding window rate limiter
├── cli.py           # Typer CLI (register, check, list, audit)
└── integrations/
    ├── langchain.py # LangChainGuard + create_guarded_agent
    ├── crewai.py    # CrewAIGuard
    └── custom.py    # @guarded decorator
```

## Data Storage

Agent-Guard uses SQLite for persistence. The default path is `agent_guard.db` in the current directory. The database contains two tables:

- **agents** — agent identities and policies (JSON)
- **audit_log** — permission check history with SHA-256 chain hashes

For production, you can specify a custom path:
```python
registry = AgentRegistry("/path/to/agent-guard.db")
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `PermissionDeniedError` on allowed tool | Check that the resource name in the policy matches exactly what the integration passes |
| Rate limit too aggressive | Increase `max_per_hour` / `max_per_day` in the ToolConstraint |
| Audit chain verification fails | An audit entry was modified outside the application — investigate tampering |
| `ModuleNotFoundError: No module named 'yaml'` | Run `pip install pyyaml` |
| Inheritance not working | Ensure `parent_agent_id` is set to a valid agent_id (not name) |
