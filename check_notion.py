#!/usr/bin/env python3
"""Check Notion pages."""
import json, urllib.request

keys = {}
with open("/home/oni/.hermes/profiles/agent-guard/.env") as f:
    for line in f:
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            keys[k] = v

token = keys.get("NOTION_API_TOKEN", "")

# Search for Agent-Guard pages
req = urllib.request.Request(
    "https://api.notion.com/v1/search",
    data=json.dumps({
        "query": "Agent-Guard",
        "filter": {"value": "page", "property": "object"}
    }).encode(),
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
        results = data.get("results", [])
        print(f"Found {len(results)} Notion pages:")
        for r in results:
            title = r.get("properties", {}).get("title", {}).get("title", [{}])
            title_text = title[0].get("plain_text", "untitled") if title else "untitled"
            print(f"  {r['id']}: {title_text}")
except Exception as e:
    print(f"Error: {e}")
