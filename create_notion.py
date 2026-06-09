#!/usr/bin/env python3
"""Create Agent-Guard project page under Projects parent in Notion."""
import json, urllib.request, os

keys = {}
with open("/home/oni/.hermes/profiles/agent-guard/.env") as f:
    for line in f:
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            keys[k] = v

token = keys.get("NOTION_API_TOKEN", "")
parent_id = "d31fc967514c4fa68cf0b20d40476b38"

# Create the main project page
page_data = {
    "parent": {"type": "page_id", "page_id": parent_id},
    "properties": {
        "title": {
            "title": [{"text": {"content": "Agent-Guard v0.1.0"}}]
        }
    },
    "children": [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Overview"}}]}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": "Agent-Guard is IAM for AI Agents — a permission and access control framework that gives developers fine-grained control over what their AI agents can do."}}]
            }
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Quick Links"}}]}
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"text": {"content": "PyPI: https://pypi.org/project/agent-guard-iam/"}}]
            }
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"text": {"content": "Install: pip install agent-guard-iam"}}]
            }
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Core Features"}}]}
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "Agent Registration with YAML policies"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "Permission checks (allow/deny) with audit logging"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "SHA-256 tamper-evident audit chain"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "Sliding window rate limiting"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "Permission inheritance with cycle detection"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "LangChain integration"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "CrewAI integration"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Stats"}}]}
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"text": {"content": "73 tests, 98% coverage"}}]
            }
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Linear Issues"}}]}
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-72: Handoff completion"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-73: Plan.md"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-74: Test coverage 80%+"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-75: LangChain tests"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-76: CrewAI tests"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-77: Permission inheritance"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-78: Rate limiting"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-79: Audit hash chain"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-80: docs/usage.md"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-81: docs/security.md"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-82: PyPI publish"}}],
                "checked": True
            }
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"text": {"content": "ONI-83: Announcement post"}}],
                "checked": False
            }
        },
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
        print(f"Created: {url}")
except Exception as e:
    print(f"Error: {e}")
    try:
        print(e.read().decode())
    except:
        pass
