#!/usr/bin/env python3
"""Upload to PyPI."""
import subprocess
import sys

# Read token from .env file
token = None
env_path = "/home/oni/.hermes/profiles/agent-guard/.env"
with open(env_path) as f:
    for line in f:
        stripped = line.strip()
        if stripped.startswith("PYPI_API_TOKEN="):
            token = stripped[len("PYPI_API_TOKEN="):]
            break

if not token:
    print("ERROR: PYPI_API_TOKEN not found in .env", file=sys.stderr)
    sys.exit(1)

print(f"Token found: {token[:10]}...{token[-5:]}")
print(f"Token length: {len(token)}")

result = subprocess.run(
    [
        "/home/oni/.hermes/profiles/agent-guard/workspace/.venv/bin/twine",
        "upload",
        "--username", "__token__",
        "--password", token,
        "dist/agent_guard_iam-0.1.0-py3-none-any.whl",
        "dist/agent_guard_iam-0.1.0.tar.gz",
    ],
    cwd="/home/oni/.hermes/profiles/agent-guard/workspace",
    capture_output=True,
    text=True,
)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
print("Exit code:", result.returncode)
