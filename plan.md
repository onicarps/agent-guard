# Agent-Guard — Build Plan
## Post-Handoff | June 8, 2026

### Current State
- 14/14 tests passing, 60% coverage
- Core engine complete: policies, registry, engine, middleware
- Integrations: LangChain, CrewAI, custom decorator
- CLI: register, check, list, audit
- Templates: admin, developer, read_only
- Git initialized, 1 commit
- Linear project: 12 issues (ONI-72 to ONI-83)

### Phase 1: Handoff Completion (ONI-72)
- [x] MEMORY.md written
- [x] Skills copied (project-lifecycle)
- [x] Research artifacts copied
- [x] Git init + initial commit
- [x] Linear project + issues created
- [ ] GitHub repo + push (BLOCKED: need valid GITHUB_TOKEN)

### Phase 2: Test Coverage 80%+ (ONI-74)
**Target: 80% coverage (currently 60%)**

- [ ] CLI tests (currently 0%) — test register, check, list, audit commands
- [ ] Middleware tests (currently 47%) — test GuardMiddleware.guard_tool, guarded decorator
- [ ] Engine escalation tests — test request_escalation with enabled/disabled policy
- [ ] Registry edge cases — update_policy, delete_agent, get_agent_by_name
- [ ] LangChain integration tests (ONI-75) — test LangChainGuard with mock tools
- [ ] CrewAI integration tests (ONI-76) — test CrewAIGuard with mock tasks

### Phase 3: Missing Features
- [ ] Permission inheritance (ONI-77) — implement parent_agent_id resolution in engine
- [ ] Rate limiting enforcement (ONI-78) — sliding window per-agent, per-tool
- [ ] Audit log hash chain (ONI-79) — SHA-256 chained hashing for tamper evidence

### Phase 4: Documentation + Launch
- [ ] docs/usage.md (ONI-80) — install, quickstart, policy examples, CLI reference
- [ ] docs/security.md (ONI-81) — threat model, permission model, audit trail
- [ ] PyPI publish (ONI-82) — build + twine upload
- [ ] Announcement post (ONI-83) — blog/social

### Branch Naming
`agent-guard/ONI-XX-description`

### Testing
```bash
pytest -xvs                          # run all tests
pytest --cov=src --cov-report=term-missing  # with coverage
```

### Commit Convention
- One feature per commit
- Format: `feat: description`, `fix: description`, `test: description`
- Reference Linear issue: `feat: rate limiting (ONI-78)`
