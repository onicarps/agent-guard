# Agent-Guard — Build Plan
## Post-Handoff | June 8, 2026

### Current State
- 73/73 tests passing (1 xfail), 98% coverage
- All core features complete: policies, registry, engine, middleware, rate limiter, audit chain
- All integrations complete: LangChain, CrewAI, custom decorator
- CLI complete: register, check, list, audit
- Templates: admin, developer, read_only YAML
- Docs: usage.md, security.md
- Git: 10 commits on master

### Phase 1: Handoff Completion (ONI-72) — COMPLETE
- [x] MEMORY.md written
- [x] Skills copied (project-lifecycle)
- [x] Research artifacts copied
- [x] Git init + initial commit
- [x] Linear project + issues created
- [x] GitHub repo + push (BLOCKED: need valid GITHUB_TOKEN — may work now with copied .env)

### Phase 2: Test Coverage 80%+ (ONI-74) — COMPLETE
- [x] CLI tests — 0% → 99%
- [x] Middleware tests — 47% → 100%
- [x] Engine escalation tests
- [x] Registry edge cases — update_policy, delete_agent, get_agent_by_name
- [x] LangChain integration tests (ONI-75) — 0% → 100%
- [x] CrewAI integration tests (ONI-76) — 0% → 100%
- [x] Bug fix: middleware metadata kwarg
- [x] Bug fix: langchain asyncio import order
- [x] Dependency: pyyaml added to pyproject.toml

### Phase 3: Missing Features — COMPLETE
- [x] Permission inheritance (ONI-77) — parent_agent_id resolution with cycle detection
- [x] Rate limiting enforcement (ONI-78) — sliding window per-agent per-resource
- [x] Audit log hash chain (ONI-79) — SHA-256 chained hashing with verify_chain()

### Phase 4: Documentation + Launch
- [x] docs/usage.md (ONI-80) — install, quickstart, policy examples, CLI reference
- [x] docs/security.md (ONI-81) — threat model, permission model, audit trail
- [ ] PyPI publish (ONI-82) — build + twine upload
- [ ] Announcement post (ONI-83) — blog/social

### Remaining Work
1. Verify GITHUB_TOKEN works → push to GitHub
2. Build and publish to PyPI
3. Announcement post
