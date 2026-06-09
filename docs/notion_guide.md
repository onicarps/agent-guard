# Agent-Guard v0.1.0 — Step-by-Step Usage Guide

## Step 1: Install

\`\`\`bash
pip install agent-guard-iam
\`\`\`

Verify the installation:
\`\`\`bash
agent-guard --help
\`\`\`

You should see 4 commands: `register`, `check`, `list`, `audit`.

---

## Step 2: Create Your First Agent

Create a new agent with a descriptive name:

\`\`\`bash
agent-guard register --name "my-first-agent"
\`\`\`

Output:
\`\`\`
✓ Registered agent: my-first-agent (a1b2c3d4...)
\`\`\`

This creates an agent with **no permissions** (default deny everything). You'll see an 8-character agent ID — you'll need this for checking permissions.

---

## Step 3: Register an Agent with a Policy

Create a YAML policy file called `policy.yaml`:

\`\`\`yaml
agent_name: "my-first-agent"
role: "developer"
permissions:
  - name: "web_search"
    type: "tool"
    effect: "allow"
  - name: "database"
    type: "database"
    effect: "allow"
  - name: "payment"
    type: "payment"
    effect: "deny"
\`\`\`

Register the agent with this policy:

\`\`\`bash
agent-guard register --name "my-first-agent" --policy-file policy.yaml
\`\`\`

The agent is now named "my-first-agent" (not the literal `{{name}}` from the template) and has the permissions you defined.

---

## Step 4: Check Permissions

Using the agent ID from Step 2:

\`\`\`bash
agent-guard check --agent-id a1b2c3d4 --resource "web_search"
# Output: ALLOW a1b2c3d4... → web_search

agent-guard check --agent-id a1b2c3d4 --resource "payment"
# Output: DENY a1b2c3d4... → payment
\`\`\`

The check is instant and also creates an audit log entry.

---

## Step 5: List All Agents

\`\`\`bash
agent-guard list
\`\`\`

Shows a table of all registered agents with their ID, name, role, and creation time.

---

## Step 6: View the Audit Log

\`\`\`bash
agent-guard audit --limit 10
\`\`\`

Shows the last 10 permission checks: who asked, what resource, and whether it was allowed or denied.

---

## Step 7: Add Rate Limiting

To prevent abuse, add rate limits to your policy:

\`\`\`yaml
permissions:
  - name: "web_search"
    type: "tool"
    effect: "allow"
    constraints:
      max_per_hour: 100
      max_per_day: 500
\`\`\`

If the agent tries to search the web for the 101st time in an hour, the check returns `DENY` and logs the rate-limited attempt.

---

## Step 8: Set Up Permission Inheritance

Create a hierarchy where child agents inherit permissions from parents:

\`\`\`bash
# Register the parent agent
agent-guard register --name "manager"
# Note the manager's agent ID

# Register a child that inherits from the parent
# (set parent_agent_id in the YAML policy)
\`\`\`

Key rules:
- Child inherits all parent permissions
- Child's explicit DENY overrides parent's ALLOW
- Child's explicit ALLOW overrides parent's DENY
- Circular references are detected and broken automatically

---

## Step 9: Use in Python Code

\`\`\`python
import asyncio
from agent_guard import AgentPolicy, AgentRegistry, PermissionEngine
from agent_guard.policies import ResourcePermission, ResourceType, PermissionEffect

async def main():
    # Initialize the registry (SQLite database)
    registry = AgentRegistry("my-agents.db")
    await registry.connect()

    # Create a policy
    policy = AgentPolicy(
        agent_name="data-analyst",
        permissions=[
            ResourcePermission(
                name="database",
                type=ResourceType.DATABASE,
                effect=PermissionEffect.ALLOW,
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
    result = await engine.check(agent_id, "database")
    print(result)  # PermissionEffect.ALLOW

    result = await engine.check(agent_id, "payment")
    print(result)  # PermissionEffect.DENY

    # Verify audit chain integrity
    is_valid = await registry.verify_chain()
    print(f"Audit chain valid: {is_valid}")  # True

    await registry.close()

asyncio.run(main())
\`\`\`

---

## Step 10: Integrate with LangChain

\`\`\`python
from agent_guard.integrations.langchain import LangChainGuard, create_guarded_agent

guard = LangChainGuard(engine, agent_id)

# Guard a single tool
guarded_search = guard.guard_tool(my_search_function)

# Or guard a list of tools at once
guarded_tools = create_guarded_agent(engine, agent_id, [tool1, tool2, tool3])
\`\`\`

---

## Step 11: Integrate with CrewAI

\`\`\`python
from agent_guard.integrations.crewai import CrewAIGuard

guard = CrewAIGuard(engine, agent_id)

@guard.guard_task
async def analyze_data(dataset: str) -> str:
    return f"Analysis of {dataset}"

@guard.guard_task_sync
def generate_report(analysis: str) -> str:
    return f"Report: {analysis}"
\`\`\`

---

## Step 12: Use the Custom Decorator

For any function, async or sync:

\`\`\`python
from agent_guard.integrations.custom import guarded

@guarded(engine, agent_id, "my-sensitive-tool")
async def sensitive_operation(data: str) -> str:
    # Only executes if agent has permission
    return process(data)
\`\`\`

---

## Pre-built Policy Templates

| Template | Description |
|----------|-------------|
| `read_only.yaml` | Read-only access to DB and files. Denies email and payments. |
| `developer.yaml` | Read/write to staging, GitHub access. Denies deploy and payments. |
| `admin.yaml` | Full access to all resource types. |

Use them:
\`\`\`bash
agent-guard register --name "my-agent" --policy-file templates/developer.yaml
\`\`\`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `PermissionDeniedError` on allowed tool | Check that the resource name in the policy matches exactly what the integration passes |
| Rate limit too aggressive | Increase `max_per_hour` / `max_per_day` in the ToolConstraint |
| Audit chain verification fails | An audit entry was modified outside the application — investigate tampering |
| `ModuleNotFoundError: No module named 'yaml'` | Run `pip install pyyaml` |
| Inheritance not working | Ensure `parent_agent_id` is set to a valid agent_id (not name) |

---

## Security Notes

- **Fail-closed by default**: If no policy exists, or no rule matches, the result is always DENY
- **Deny precedence**: Explicit DENY rules always override ALLOW rules
- **Tamper-evident audit**: SHA-256 chained hashing detects any modification or deletion of audit entries
- **Parameterized SQL**: All database queries use parameterized statements — no SQL injection risk
- **Safe YAML**: Uses `yaml.safe_load()` — no arbitrary code execution from policy files
