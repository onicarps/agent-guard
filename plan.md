# Agent-Guard — Build Plan
## v0.1.0 | June 8, 2026

### Status: PUBLISHED ✅

**Package:** [agent-guard-iam on PyPI](https://pypi.org/project/agent-guard-iam/)
**Install:** `pip install agent-guard-iam`
**Tests:** 82 passed, 1 xfailed, 99% coverage

### Phase 1: Handoff Completion (ONI-72) — COMPLETE
- [x] MEMORY.md written, skills copied, research artifacts copied
- [x] Git init + initial commit, Linear project + issues created
- [x] GitHub repo + push

### Phase 2: Test Coverage 80%+ (ONI-74) — COMPLETE
- [x] CLI tests (0% → 99%), middleware tests (47% → 100%)
- [x] Engine escalation tests, registry edge cases
- [x] LangChain integration tests (ONI-75), CrewAI integration tests (ONI-76)

### Phase 3: Missing Features — COMPLETE
- [x] Permission inheritance with cycle detection (ONI-77)
- [x] Rate limiting enforcement — sliding window (ONI-78)
- [x] Audit log hash chain — SHA-256 + tamper detection (ONI-79)

### Phase 4: Documentation + Launch — COMPLETE
- [x] docs/usage.md (ONI-80), docs/security.md (ONI-81)
- [x] PyPI publish as `agent-guard-iam` v0.1.0 (ONI-82)
- [ ] Announcement post (ONI-83) — remaining

### Pre-Publish Audit — ALL ISSUES RESOLVED
- **Critical (C1-C4):** Template name substitution, duplicate hash fn, doc imports, audit lock
- **Warnings (W1-W6):** All 6 fixed and verified by subagent
  - W1: verify_chain previous-hash + deletion tests
  - W2: Inherited DENY + operation-deny tests
  - W3: Sync @guarded in async context tests
  - W4: Rate limiter asyncio.Lock + concurrent test
  - W5: agent_name UNIQUE constraint
  - W6: Grandparent DENY beats parent ALLOW (flat-bag documented)

### Notion Documentation
- Project page: https://app.notion.com/p/Agent-Guard-v0-1-0-37ae2527f31781cc83ecd7283ad69129
- Step-by-Step Usage Guide (12 steps)
- Security Model (threats, permissions, audit)
- Sample Use Cases (8 real-world scenarios)

### Remaining
- ONI-83: Announcement post
- v0.1.1: Nice-to-have improvements from audit suggestions (S1-S12)
