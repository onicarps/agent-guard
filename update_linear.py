#!/usr/bin/env python3
"""Update Linear issues to Done."""
import json, urllib.request

keys = {}
with open("/home/oni/.hermes/profiles/agent-guard/.env") as f:
    for line in f:
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            keys[k] = v

linear_key = keys.get("LINEAR_API_KEY", "")
DONE_ID = "7565664d-c0be-467b-a15e-4afd34bf0087"

# Map issue identifiers to internal IDs
issue_map = {
    "ONI-72": "55028922-480f-42fd-a05e-7081f984ccef",
    "ONI-73": "78560e73-d22b-4808-811e-86180529ac43",
    "ONI-74": "a79b48f4-90f9-4558-8746-ae2fdd413773",
    "ONI-75": "cd88e444-026e-4e6a-93af-f65864161121",
    "ONI-76": "aee6b403-0c96-476b-8b80-1c35dd8f6d98",
    "ONI-77": "6a96a5e3-d6a4-42c4-8f56-e873a103d9db",
    "ONI-78": "c9fe3f78-8982-4a08-b715-43b20df30dce",
    "ONI-79": "17a8bbd1-1538-49e2-9a24-22d53a2527dc",
    "ONI-80": "61096953-ab73-4843-8ba7-84a3cc4e01c9",
    "ONI-81": "71a09090-a03f-49be-9f1a-f115881fdb61",
    "ONI-82": "388056eb-d653-4efe-a14e-d19201579899",
}

# Skip ONI-83 (announcement post) — still backlog
skip = {"ONI-83"}

for issue_id, internal_id in issue_map.items():
    if issue_id in skip:
        print(f"  {issue_id}: SKIPPED (still backlog)")
        continue
    
    req = urllib.request.Request(
        "https://api.linear.app/graphql",
        data=json.dumps({
            "query": f'mutation {{ issueUpdate(id: \"{internal_id}\", input: {{ stateId: \"{DONE_ID}\" }}) {{ success }} }}'
        }).encode(),
        headers={"Authorization": linear_key, "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            success = data.get("data", {}).get("issueUpdate", {}).get("success")
            print(f"  {issue_id}: {'DONE' if success else 'FAILED'}")
    except Exception as e:
        print(f"  {issue_id}: ERROR — {e}")
