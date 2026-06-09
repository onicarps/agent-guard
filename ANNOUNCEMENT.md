# Agent-Guard v0.1.1 — IAM for AI Agents is Here

**We just published the first open-source permission and access control framework purpose-built for AI agents.**

## The Problem

AI agents are getting more powerful — and more dangerous. We've all seen the stories: an AI assistant that was supposed to read emails instead sent spam to everyone in your contacts. A coding agent that was given access to a staging database somehow ended up dropping production tables.

The worst part? **There was no permission framework stopping it.**

Existing IAM solutions (AWS IAM, Okta, Auth0) were built for humans logging into dashboards. They don't understand AI agents making thousands of autonomous tool calls per hour. You can't ask an OAuth consent screen for permission every time your agent wants to call an API.

## The Solution: Agent-Guard

Agent-Guard asks a different question. Instead of "is this output good?" (impossible to verify), it asks **"is this agent allowed to do this?"** (objective, enforceable).

Here's what that looks like in practice:

### 1. Define Policies in YAML

```yaml
agent_name: "customer-support-bot"
role: "support"
permissions:
  - name: "read_ticket"
    type: "tool"
    effect: "allow"
  - name: "send_reply"
    type: "tool"
    effect: "allow"
    constraints:
      max_per_hour: 200
  - name: "delete_ticket"
    type: "tool"
    effect: "deny"
  - name: "refund_money"
    type: "payment"
    effect: "deny"
escalation:
  enabled: true
  approver: "support-lead"
  max_escalations_per_day: 5
```

This bot can read tickets and send up to 200 replies per hour. It can **never** delete tickets or process refunds — even if a prompt injection attack tries to make it.

### 2. Enforce at the Integration Layer

Agent-Guard works with LangChain, CrewAI, or any custom agent:

```python
from agent_guard import AgentRegistry, PermissionEngine
from agent_guard.integrations.crewai import CrewAIGuard

# Register agent with policy
registry = AgentRegistry("agents.db")
await registry.connect()
policy = register_from_template("support-bot", "support.yaml")
agent_id = await registry.register_agent(policy)

# Guard CrewAI tasks
engine = PermissionEngine(registry)
guard = CrewAIGuard(engine, agent_id)

@guard.guard_task
async def handle_ticket(ticket_id: str) -> str:
    return await read_ticket(ticket_id)

@guard.guard_task_async
async def send_reply(ticket_id: str, message: str) -> str:
    return await send_message(ticket_id, message)
```

Every tool call is checked. Unauthorized calls get `PermissionDeniedError`. All decisions are logged.

### 3. Tamper-Evident Audit Trail

Every permission check creates a log entry chained with SHA-256 hashing. If anyone modifies or deletes an entry, `verify_chain()` detects it instantly. This matters for compliance: you can prove to auditors that your AI advisor never accessed SSN data, and the logs were never altered.

### 4. Permission Inheritance

Create hierarchies where child agents inherit parent permissions. Child permissions override parent permissions. Circular references are detected and broken automatically.

## What's in v0.1.1

- **Full CLI**: register, check, list, audit, delete
- **LangChain integration**: Guard any LangChain tool
- **CrewAI integration**: Guard any CrewAI task
- **Custom decorator**: @guarded() for any function
- **Sliding window rate limiting**: Per-agent, per-resource
- **Permission inheritance**: Parent-child hierarchies with cycle detection
- **SHA-256 audit chain**: Tamper-evident logging
- **93 tests, 98% coverage**
- **Pre-built templates**: read_only, developer, admin

## Get Started

```bash
pip install agent-guard-iam
```

Python API:

```python
from agent_guard import register_from_template, AgentRegistry, PermissionEngine

policy = register_from_template("my-agent", "developer.yaml")
registry = AgentRegistry("agents.db")
await registry.connect()
agent_id = await registry.register_agent(policy)

engine = PermissionEngine(registry)
result = await engine.check(agent_id, "database", "read")
# PermissionEffect.ALLOW or PermissionEffect.DENY
```

## Links

- PyPI: https://pypi.org/project/agent-guard-iam/
- GitHub: https://github.com/onicarps/agent-guard
- Install: pip install agent-guard-iam

## Why We Built This

We interviewed 5 developers building AI agents. 80% said the same thing: **"I have no way to control what my agent does."** They're shipping agents with all-or-nothing tool access because there was no middle ground.

Agent-Guard is that middle ground. Try it today.

---

Built by the ONI team. MIT licensed. PRs welcome.
