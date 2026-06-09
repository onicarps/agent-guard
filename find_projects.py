#!/usr/bin/env python3
"""List all pages accessible to the integration."""
import json, urllib.request

keys = {}
with open("/home/oni/.hermes/profiles/agent-guard/.env") as f:
    for line in f:
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            keys[k] = v

token = keys.get("NOTION_API_TOKEN", "")

# List all pages (no filter)
req = urllib.request.Request(
    "https://api.notion.com/v1/search",
    data=json.dumps({
        "query": "",
        "filter": {"value": "page", "property": "object"},
        "page_size": 10
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
        print(f"Found {len(results)} pages:")
        for r in results:
            props = r.get("properties", {})
            for prop_name, prop_val in props.items():
                if prop_val.get("type") == "title":
                    title_list = prop_val.get("title", [])
                    title_text = title_list[0].get("plain_text", "untitled") if title_list else "untitled"
                    print(f"  {r['id']}: {title_text}")
                    break
except Exception as e:
    print(f"Error: {e}")
