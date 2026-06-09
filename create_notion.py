#!/usr/bin/env python3
"""Create Notion page for Agent-Guard."""
import json, urllib.request, os

keys = {}
with open("/home/oni/.hermes/profiles/agent-guard/.env") as f:
    for line in f:
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            keys[k] = v

token = keys.get("NOTION_API_TOKEN", "")
workspace_id = keys.get("NOTION_WORKSPACE_ID", "")

# Create a page with project summary
content = """# Agent-Guard v0.1.0

**IAM for AI Agents** — permission and access control framework.

## What It Does

Agent-Guard gives developers fine-grained control over what their AI agents can do. Instead of asking "is this output good?" (subjective), Agent-Guard asks "is this agent allowed to do this?" (objective, enforceable).

## Core Features

- **Agent Registration** — Register agents with YAML permission policies
- **Permission Checks** — Check allow/deny before every tool call
- **Audit Logging** — Every decision logged with SHA-256 tamper-evident chain
- **Rate Limiting** — Sliding window per-agent, per-tool
- **Permission Inheritance** — Parent-child agent hierarchies with cycle detection
- **Framework Integrations** — LangChain, CrewAI, custom decorator

## Status: v0.1.0 Published ✅

- PyPI: https://pypi.org/project/agent-guard-iam/
- Install: `pip install agent-guard-iam`
- 73 tests, 98% coverage
- All Phase 1-4 deliverables complete

## Linear Project

Issues ONI-72 through ONI-82 all marked Done.
Remaining: ONI-83 (announcement post)

## Links

- PyPI: https://pypi.org/project/agent-guard-iam/
- Usage: See docs/usage.md
- Security: See docs/security.md
"""

page_data = {
    "parent": {"type": "workspace_id", "workspace_id": workspace_id} if workspace_id else {"type": "workspace", "workspace": True},
    "properties": {
        "title": {
            "title": [{"text": {"content": "Agent-Guard v0.1.0"}}]
        }
    },
    "children": [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": line}}]
            }
        } for line in content.split("\n") if line.strip()
    ]
}

req = urllib.request.Request(
    "https://api.notion.com/v1/pages",
    data=json.dumps(page_data).encode(),
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    },
    method="POST"
)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        page_id = data.get("id", "unknown")
        url = data.get("url", "unknown")
        print(f"Created Notion page: {url}")
except Exception as e:
    print(f"Error: {e}")
    try:
        print(e.read().decode())
    except:
        pass
