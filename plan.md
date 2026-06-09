# Agent-Guard — Build Plan
## v0.1.1 | June 8, 2026

### Status: READY FOR PUBLISH ✅

**Package:** [agent-guard-iam on PyPI](https://pypi.org/project/agent-guard-iam/)
**Install:** `pip install agent-guard-iam`
**Tests:** 93 passed, 1 xfailed, 98% coverage

### All Phases Complete
- [x] Phase 1: Handoff (ONI-72)
- [x] Phase 2: Test Coverage 80%+ (ONI-74) — 98% achieved
- [x] Phase 3: Missing Features (ONI-77, 78, 79)
- [x] Phase 4: Docs + Launch (ONI-80, 81, 82)

### Pre-Publish Audit — ALL RESOLVED
- **Critical (C1-C4):** Template name substitution, duplicate hash fn, doc imports, audit lock
- **Warnings (W1-W6):** All 6 fixed
  - W1: verify_chain previous-hash + deletion tests
  - W2: Inherited DENY + operation-deny tests
  - W3: Sync @guarded in async context tests
  - W4: Rate limiter asyncio.Lock + concurrent test
  - W5: agent_name UNIQUE constraint
  - W6: Grandparent DENY beats parent ALLOW test

### v0.1.1 Suggestions — ALL IMPLEMENTED
- [x] S1: Template smoke tests
- [x] S2: register_from_template() Python helper
- [x] S3: Standard import time (no __import__ hack)
- [x] S4: Parameterized Callable types in integrations
- [x] S5: Registry._require_connected() — fail loudly
- [x] S6: agent-guard delete CLI command
- [x] S7: __main__ block subprocess test
- [x] S8: Friendlier ISO 8601 timestamps in CLI
- [x] S12: Parse metadata_json in get_audit_log

### Notion Documentation
- Project page: Agent-Guard v0.1.0
- Step-by-Step Usage Guide (12 steps)
- Security Model (threats, permissions, audit)
- Sample Use Cases (8 real-world scenarios)

### Remaining
- ONI-83: Announcement post
- Push to GitHub
- Rebuild + republish to PyPI as v0.1.1
