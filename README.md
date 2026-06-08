# Agent-Guard

**IAM for AI agents** — permission and access control framework.

## Quick Start

```bash
# Install
pip install agent-guard-iam

# Register an agent
agent-guard register --name "my-agent" --role developer --policy-file policy.yaml

# Check permission
agent-guard check --agent-id <id> --resource "send_email"

# List agents
agent-guard list

# View audit log
agent-guard audit
```

## Policy Example

```yaml
agent_name: "customer-support-agent"
role: "support"
permissions:
  - name: "send_email"
    type: "tool"
    effect: "allow"
    constraints:
      max_per_hour: 100
  - name: "charge_card"
    type: "payment"
    effect: "deny"
```

## License
MIT
