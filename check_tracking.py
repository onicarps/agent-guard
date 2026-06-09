#!/usr/bin/env python3
"""Check Linear issues."""
import os, json, urllib.request

keys = {}
with open("/home/oni/.hermes/profiles/agent-guard/.env") as f:
    for line in f:
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            keys[k] = v

linear_key = keys.get("LINEAR_API_KEY", "")

# Simple query - just issues
query = {
    "query": """query {
        issues(first: 30) {
            nodes {
                identifier
                title
                state { name }
                project { name }
            }
        }
    }"""
}

req = urllib.request.Request(
    "https://api.linear.app/graphql",
    data=json.dumps(query).encode(),
    headers={"Authorization": linear_key, "Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        issues = data.get("data", {}).get("issues", {}).get("nodes", [])
        print(f"Found {len(issues)} issues:")
        for i in issues:
            proj = i.get("project", {}) or {}
            print(f"  {i['identifier']}: {i['title']} [{i['state']['name']}] (Project: {proj.get('name', 'none')})")
except Exception as e:
    print(f"Error: {e}")
    # Try to read error body
    try:
        print(e.read().decode())
    except:
        pass
