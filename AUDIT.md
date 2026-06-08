# Agent-Guard v0.1.0 — Pre-Publish Audit Report

**Audit date:** 2026-06-08
**Workspace:** `/home/oni/.hermes/profiles/agent-guard/workspace/`
**Scope:** read-only review of every source file, test file, config file, template, and doc.
**Test baseline reproduced:** `73 passed, 1 xfailed`, total coverage **98%** (442 stmts / 10 missed).
**Lint baseline reproduced:** `ruff check src tests` → **16 errors** (all `F401`/`F841` unused imports/vars).

---

## Critical Issues (must fix before publish)

### C1. CLI ignores `--name` and never substitutes `{{name}}` in template policies
- **Files:** `src/agent_guard/cli.py:30-50`, all of `templates/*.yaml`
- **Description:** When a `--policy-file` is supplied, the CLI does:
  ```python
  with open(policy_file) as f:
      data = yaml.safe_load(f)
  policy = AgentPolicy(**data)
  ```
  The `--name` typer option is required but is *not* threaded into `data`, and the literal string
  `{{name}}` from the templates is never substituted. The success line on the next statement
  (`f"Registered agent: {name} ..."`) prints the CLI argument `name`, which masks the bug —
  the agent is in fact registered with `agent_name = "{{name}}"`.
- **Reproduction (verified):**
  ```bash
  agent-guard register --name realname --policy-file templates/admin.yaml
  # stdout: ✓ Registered agent: realname (...)
  # DB row: agent_name = '{{name}}'   <-- wrong
  ```
- **Impact:** Every agent registered from any of the three shipped templates ends up named
  literally `"{{name}}"`. Subsequent lookups by name (`get_agent_by_name`) collide across
  every template-registered agent. The README "Quick Start" and `docs/usage.md` both lead
  users straight into this bug. Mission spec §6 explicitly calls this out:
  *"Are the `{{name}}` placeholders handled correctly by the CLI?"* — they are not.
- **Fix sketch:** before `AgentPolicy(**data)`, do
  `for k, v in list(data.items()): data[k] = v.replace("{{name}}", name) if isinstance(v, str) else v`
  (or use `str.format` / Jinja). Also override `data["agent_name"] = name` so `--name` wins.

### C2. Duplicate `_compute_chain_hash` — shadowed dead code with a *different* hash algorithm
- **File:** `src/agent_guard/registry.py:13-26` (first definition) vs `:244-267` (second definition)
- **Description:** The module defines `_compute_chain_hash` twice. The second definition
  rebinds the name, so the first definition is unreachable (lines 25-26 are exactly the
  "missing" lines in the coverage report). The two implementations are *not* equivalent:
  * Top one: keyword-or-positional, `f"{entry_id}{agent_id}{resource}{operation}{effect}{timestamp}{metadata_json}{previous_hash}"`
    (no separator, plain `str(operation)` and `str(timestamp)`).
  * Bottom one: keyword-only (`*`), pipe-joined,  `operation or ""`, `repr(timestamp)`.

  If anyone inadvertently imports or calls the top one (e.g. via partial reload, monkey-patch,
  or future refactor that removes the second), audit chains computed with one will not validate
  with the other. The collision is silent and only differs in formatting — exactly the kind of
  subtle bug that breaks a tamper-evidence guarantee.
- **Impact:** On its own, the running code is correct (last def wins). However, this is a
  **security-critical code-path that ships with two non-equivalent implementations and dead
  code claiming to be the canonical one**. Any future maintainer who deletes the bottom
  definition will silently rotate the hash format and invalidate every existing audit DB.
- **Fix:** delete lines 13-26; keep only the bottom definition (preferably move it above
  `AgentRegistry` for readability) and add a unit test that pins the exact hash format.

### C3. `docs/usage.md` advertises framework integration import paths that do not exist
- **File:** `docs/usage.md` lines for the LangChain and CrewAI sections.
- **Description:** Documented imports:
  ```python
  from agent_guard.langchain import LangChainGuard, create_guarded_agent
  from agent_guard.crewai import CrewAIGuard
  ```
  Actual module locations are `agent_guard.integrations.langchain` and
  `agent_guard.integrations.crewai`. There is no re-export in `agent_guard/__init__.py`
  and no `agent_guard/langchain.py` / `agent_guard/crewai.py`. Verified:
  ```
  >>> from agent_guard.langchain import LangChainGuard
  ModuleNotFoundError: No module named 'agent_guard.langchain'
  ```
- **Impact:** Every user who copy-pastes the documented framework example crashes on the
  first import. This is the headline feature for the two named integrations.
- **Fix:** either change the docs to `agent_guard.integrations.langchain` /
  `.integrations.crewai`, *or* (preferred for a public API) re-export the symbols in
  `src/agent_guard/__init__.py` and add corresponding shim modules.

### C4. Hash-chain race in `AgentRegistry.log_audit` — concurrent calls produce branched chains
- **File:** `src/agent_guard/registry.py:170-205` (`log_audit`)
- **Description:** `log_audit` reads the latest `chain_hash` and then inserts a new row, but
  the read and the write are *not* in a transaction and there is no application-level lock.
  Two concurrent `await registry.log_audit(...)` calls (very normal under any concurrent
  agent workload, e.g. `asyncio.gather(...)`) can interleave:
  ```
  T1: SELECT chain_hash -> H
  T2: SELECT chain_hash -> H        # same H
  T1: INSERT (..., previous=H, chain=h1)
  T2: INSERT (..., previous=H, chain=h2)
  ```
  Now two entries share the same `previous_hash`, the chain is no longer linear, and
  `verify_chain()` will fail (`row["previous_hash"] != expected_prev` on the second sibling).
- **Impact:** Tamper-evidence — the headline of `docs/security.md` §T3 — silently breaks
  under concurrency. There is no test that exercises concurrent `log_audit`. Because the
  `PermissionEngine.check` flow always logs, *any* concurrent permission check storms can
  hit this. The DB ends up with a permanently invalid chain.
- **Fix:** wrap `SELECT … LIMIT 1` + `INSERT` in `BEGIN IMMEDIATE` (aiosqlite supports
  `db.execute("BEGIN IMMEDIATE")`), or guard with an `asyncio.Lock` instance attached to
  the registry. Add a regression test that runs ~50 `log_audit` calls under
  `asyncio.gather` and then asserts `verify_chain()`.

---

## Warnings (should fix before publish)

### W1. `verify_chain` previous-hash branch is untested
- **File:** `src/agent_guard/registry.py:217` (the `if row["previous_hash"] != expected_prev: return False`)
- **Coverage:** missing line 217 in the report. The single tampering test in
  `tests/test_audit_chain.py::test_chain_verify_tampered` overwrites `chain_hash`, which
  trips the *recomputed-hash* branch (line 222) but never the previous-link branch.
  A test that sets `previous_hash` to garbage on row 2 (or deletes row 2 entirely)
  is needed. Without it, the headline "deletion is detected" claim in
  `docs/security.md` §T3 is unverified by tests.

### W2. `policies.AgentPolicy.check_permission` — inherited DENY and inherited operation-deny untested
- **File:** `src/agent_guard/policies.py` lines 81 and 85-86 (the two missing-coverage
  blocks in the report).
- **Description:** Lines 81 and 85-86 implement:
  * inherited explicit DENY on the resource → DENY
  * inherited ALLOW with `allowed_operations` constraint mismatch → DENY
  Neither is hit by any existing test. `tests/test_inheritance.py::test_inheritance_child_override`
  uses a DENY on the *child*, not on a parent. There is no test where the parent denies an
  operation while the child has no rule. The risk is real: an explicit parent DENY that
  silently gets ignored would be a permission-bypass.
- **Suggested test cases:**
  1. Parent denies `read_db`, child has no rule → engine.check → DENY.
  2. Parent allows `database` with `allowed_operations=["read"]`, child has no rule,
     `engine.check(child, "database", "write")` → DENY.

### W3. Sync `guarded` decorator — running-loop branch untested and behaviorally suspect
- **File:** `src/agent_guard/integrations/custom.py:31-40` (the missing-coverage 38-40 block)
- **Description:** When the sync wrapper detects an already-running loop, it shells out to a
  `ThreadPoolExecutor` running `asyncio.run(...)` from a fresh thread. This works in CPython,
  but:
  * The `loop` variable is bound and never used (ruff `F841`).
  * Every guarded sync call inside an event loop spawns a thread, opens a *new* SQLite
    connection (because the engine reuses the registry which holds a single connection),
    and runs `assert_allowed`. With aiosqlite's connection-per-thread model this can
    deadlock if the registry's `_db` is bound to the original loop. There is no test
    coverage for this path at all (`@guarded` sync inside async context).
  * The `concurrent.futures.ThreadPoolExecutor` is created and torn down on every call
    — measurable overhead per tool call.
- **Risk:** silent runtime hang or `RuntimeError: cannot schedule new futures after
  interpreter shutdown` in production. At minimum, add a test that wraps a sync function
  with `@guarded` and calls it from inside an `async def`.

### W4. `RateLimiter` is not thread/async safe
- **File:** `src/agent_guard/rate_limiter.py:12-50`
- **Description:** `_windows: dict[tuple, list[float]]` and the `timestamps[:] = [...]`
  filter+`append` are not atomic across `await` points (the limiter is sync, but it is
  called from async contexts; multiple coroutines on the same loop can nevertheless
  observe inconsistent counts if the limiter is later threaded). More importantly, the
  state is process-local and not persisted — `docs/security.md` §"Limitations" admits
  this. That's fine, but the limit *check* and *record* are also not atomic: with two
  near-simultaneous coroutines we may see two `True` returns for what should be the
  10th and "11th" (denied) call.
- **Fix:** wrap the body of `check` in a single critical section, or move the state
  to async-safe primitives.

### W5. `register_agent` does not enforce `agent_name` uniqueness, but `get_agent_by_name` returns "first"
- **Files:** `src/agent_guard/registry.py:79-87` (`register_agent`) and `:99-104`
  (`get_agent_by_name`).
- **Description:** The `agents` table has `agent_id` PK but no `UNIQUE` constraint on
  `agent_name`. The CLI lets you register the same name many times (each gets a new
  UUID), and `get_agent_by_name` then returns whichever row SQLite returns first
  (effectively non-deterministic). Combined with C1 above, every template-registered
  agent shares the literal name `{{name}}`, and `get_agent_by_name("{{name}}")` returns
  one of them at random.
- **Fix:** add `UNIQUE` on `agent_name` in the schema *or* rename the helper to
  `get_first_agent_by_name` and document the caveat. Tests should cover the
  duplicate-name path.

### W6. Inheritance ordering allows ancestor DENY to outrank own ALLOW (or vice versa) depending on `merged` order
- **File:** `src/agent_guard/policies.py:55-89`
- **Description:** `engine.check` resolves inherited permissions with `_skip_self=True`,
  so `check_permission` receives a flat list of ancestor permissions (most-specific
  first). The current implementation treats this list as one big bag: any DENY in the
  bag wins over any ALLOW in the bag. So a *grandparent's* DENY beats a *parent's*
  ALLOW. The docs (`docs/security.md` "Inheritance Rules") imply level-by-level
  resolution — they list "Parent denies, child allows → Child ALLOW wins" — but the
  same rule does not apply between grandparent and parent because they are flattened.
  This is technically consistent with "explicit DENY precedence" but:
  * It is NOT what the threat model says.
  * No test exercises grandparent-DENY-vs-parent-ALLOW.
- **Suggested fix:** Either resolve level-by-level (each ancestor's permissions form a
  layer; child layer beats parent layer for the same resource) and update tests, or
  document the flat-bag rule explicitly in `docs/security.md`. Add a test for the
  ambiguous case and decide.

### W7. 16 ruff `F401`/`F841` warnings — none auto-fixed before "publish"
- **Files:** `src/agent_guard/cli.py` (5 unused imports), `engine.py` (3),
  `integrations/custom.py` (1 + 1 F841 unused `loop`), `integrations/langchain.py` (1),
  `middleware.py` (2), `policies.py` (1), `registry.py` (1), `tests/test_rate_limiter.py` (1).
- **Description:** Run `.venv/bin/python -m ruff check src tests` to reproduce. None of
  these are bugs on their own, but `pyproject.toml` advertises ruff as a dev tool and the
  AGENTS.md states "ruff linting" is part of the style; shipping a 0.1.0 with 16 lint
  errors on the first PR is a bad signal. Notably:
  * `middleware.py` imports `PermissionDeniedError` (unused) — looks like the author
    intended to surface it from this module; either re-export it or remove.
  * `engine.py` imports `time` and `AgentPolicy` and `ResourceType` — none used.
  * `integrations/custom.py` `loop = asyncio.get_running_loop()` — only the truthiness
    of the call's success matters; either use `loop` or rewrite as a bare call.

### W8. `docs/usage.md` — broken Python snippets
- **File:** `docs/usage.md`
- **Issues found while mentally executing the snippets:**
  1. The "Permission Inheritance" snippet uses `ToolConstraint(allowed_operations=["write"])`
     without importing `ToolConstraint`.
  2. The same snippet builds the child with `effect=PermissionEffect.DENY` plus
     `constraints={"allowed_operations": ["write"]}`. With the current
     `policies.AgentPolicy.check_permission`, an unconditional DENY on `"database"`
     ignores constraints — the comment "deny only applies to write" is **wrong**:
     the child will be denied for *any* operation on `database`, including `read`.
  3. The "LangChain" snippet decorates with `@guard.guard_tool` (no parens), but
     `guard_tool` is a method that takes the function — using it as a decorator works
     by accident, but combined with `@tool` from `langchain.tools` (which returns a
     `BaseTool`, not a callable that `LangChainGuard.guard_tool` can wrap with a
     coroutine) it will raise at decoration time. Worth a quick integration smoke test.
  4. The "List Agents" sample output shows `Created` as a Unix epoch float — fine, but
     the AGENTS.md uses `created_at` while the table heading uses `Created`. Minor.
- **Recommendation:** treat each snippet as a doctest target; either run them in CI or
  rewrite them to be true.

### W9. `engine.py` lazy import via `__import__` in `cli.py:64`
- **File:** `src/agent_guard/cli.py:64`
- **Description:**
  ```python
  engine = __import__("agent_guard.engine", fromlist=["PermissionEngine"]).PermissionEngine(registry)
  ```
  There is no circular-import problem (cli only imports from `policies`/`registry` at
  module level; `engine` does not import `cli`), so the `__import__` dance is purely
  obfuscation. Replace with `from .engine import PermissionEngine` at the top of the file.

### W10. `register_agent` failure on duplicate UUID is not caught
- **File:** `src/agent_guard/registry.py:79-87`
- **Description:** UUIDs are unique in practice, but `policy.agent_id` is user-supplied
  in `update_policy`-style flows; if a caller passes an `AgentPolicy(agent_id=existing)`,
  `register_agent` raises `aiosqlite.IntegrityError` with no friendlier wrapping. The
  CLI surfaces a raw traceback. Worth wrapping at least at the CLI layer.

---

## Suggestions (nice to fix)

### S1. Templates: validate them in CI
The mission asks "do they parse correctly with `yaml.safe_load()` and pass `AgentPolicy(**data)`?".
I verified this manually: all three templates parse cleanly with `yaml.safe_load` and
construct an `AgentPolicy` (modulo the `{{name}}` bug above). There is no automated test
asserting this, however; one parametrized test over the templates dir would prevent regressions.

### S2. Add a `register_from_template(name, template_path)` helper
With C1 fixed, expose a small Python helper that reads a YAML template, substitutes
`{{name}}` and any other placeholders, and returns an `AgentPolicy`. Document it in
`docs/usage.md`. The CLI can then re-use the helper and the duplication between CLI
and library is removed.

### S3. Replace `__import__('time').time()` default factories
- **File:** `src/agent_guard/policies.py:96`
- The pattern
  `timestamp: float = Field(default_factory=lambda: __import__('time').time())`
  works but is unidiomatic; `import time` at module top + `default_factory=time.time` is
  the standard Pydantic v2 form.

### S4. Consistent typing: `Callable` without parameters
`middleware.py`, `integrations/langchain.py`, `integrations/crewai.py`, and `custom.py`
all use bare `Callable` for tool functions. With `mypy strict` this is `Callable[..., Any]`
implicitly; for clearer types, parameterize: `Callable[..., Awaitable[Any]]` for async
tools and `Callable[..., Any]` for sync.

### S5. `AgentRegistry` should fail loudly if methods are called before `connect()`
If any method is invoked while `self._db is None`, the failure is `AttributeError: 'NoneType'
object has no attribute 'execute'`. A small `_require_connected()` helper raising a clear
`RuntimeError("AgentRegistry not connected; call await connect() first")` would make the
API much more debuggable.

### S6. `cli.py`: `list` shadows the builtin
`@app.command()\ndef list() -> None: ...` works (Typer renames the command to `list`),
but it shadows the builtin `list` for the rest of the module. There are no other uses
today; rename to `list_agents` (and add `name="list"` to `@app.command()`) to be safe.

### S7. `pyproject.toml` is missing a few publication essentials
- No `authors` / `maintainers` / `urls` (homepage, repository, issues).
- No `keywords` (helps PyPI discoverability for "AI agents", "permissions", "IAM").
- No `classifiers` (`Development Status :: 3 - Alpha`, `License :: OSI Approved :: MIT License`,
  `Programming Language :: Python :: 3.11`, `Programming Language :: Python :: 3.12`,
  `Topic :: Security`).
- The `[project.optional-dependencies] crewai` pin is `crewai>=0.1` which is permissive to
  the point of meaningless (current crewai is several majors past 0.1 with breaking changes);
  the integration is tested only against an inline shim, not the real crewai package.
- `pytest-xdist` is in dev dependencies but `addopts = "-xvs ..."` includes `-x` (stop on
  first failure) and `-s` (no capture), which is fine for local but bad CI defaults.

### S8. Doc/code naming: `Created` column is a raw float epoch
`cli.py:audit` and `cli.py:list` print `entry["timestamp"]` and `agent["created_at"]` as
raw floats. `time.ctime()` or `datetime.datetime.fromtimestamp(..., tz=UTC).isoformat()`
would be much friendlier and avoids the "1717831234.567" output shown in the docs.

### S9. Cover the `if __name__ == "__main__":` line in cli (line 139)
Trivial — invoke the module via `python -m agent_guard.cli --help` from a test using
`subprocess.run`. Brings `cli.py` to 100% and removes the only nontrivial gap.

### S10. `agent-guard delete` command is missing
The library exposes `AgentRegistry.delete_agent` (with a test), but the CLI has no
corresponding command. For a v0.1 published package, the asymmetry is mildly confusing.

### S11. Tests: missing edge cases
- No test for empty/`None`/whitespace `agent_name` (Pydantic accepts `""` today, then
  registers; surprising).
- No test for very large `policy_json` (e.g., 1k permissions) to verify SQLite TEXT
  column has no surprises.
- No test for SQLite locked DB (e.g., second registry on same file).
- No test for path-traversal/relative paths in `--policy-file` (currently fine because
  Python's `open` is used directly, but a test would make this explicit).
- No concurrent-`log_audit` test (see C4).

### S12. `metadata` JSON in audit_log is opaque
`get_audit_log` returns the raw `metadata_json` string — callers always have to
`json.loads` themselves. Returning the parsed dict (or an `AuditEntry`) would be a
nicer surface. The CLI ignores metadata in its output entirely.

---

## Positive Findings (genuinely well done)

- **Coverage is real, not lipstick.** 73 deliberate tests with focused fixtures, fixture
  cleanup via `os.unlink`, and asyncio-aware fixtures. Testing strategy aligns
  with `AGENTS.md`.
- **Test isolation is correct.** Every async test uses a tempfile DB, and
  `tests/integrations/test_langchain.py::TestLangChainGuardSync` properly addresses the
  sync-fixture-vs-async-engine caveat by running its own `asyncio.run` per setup.
- **Pydantic v2 modeling is clean.** `AgentPolicy`, `ResourcePermission`,
  `EscalationPolicy`, `AuditEntry` all use proper field defaults via `Field(default_factory=...)`.
  Enums for `PermissionEffect` and `ResourceType` are correct.
- **Fail-closed defaults.** `check_permission` returns `DENY` on every fall-through.
  No path returns `ALLOW` implicitly. The threat model in `docs/security.md` is
  consistent with the implementation on this point.
- **Cycle detection.** `resolve_permissions` correctly uses a visited set; the test
  `test_inheritance_circular` actually mutates a parent into a cycle and verifies the
  check terminates and returns `DENY`. Nice.
- **Schema migration is forward-compatible.** `connect()` runs `ALTER TABLE … ADD COLUMN`
  with a `try/except` for `previous_hash` and `chain_hash`, allowing old databases to be
  upgraded silently.
- **Parameterized SQL everywhere.** No string-formatted SQL anywhere in the codebase —
  `?` placeholders are used uniformly. No SQL injection risk found.
- **`yaml.safe_load`** is used (never `yaml.load`/`Loader=Loader`), so YAML
  deserialization is safe.
- **Docs are substantial.** `docs/usage.md` and `docs/security.md` are detailed,
  cover threats T1–T5, and articulate the permission resolution order. The threat-model
  table format makes the security model auditable.
- **Rate limiter is genuinely sliding-window.** The `cutoff` and per-window counts are
  correct; `test_rate_limiter_sliding_window` verifies wraparound after 1h+1s.
- **Audit-chain mechanics are correct.** Modulo C2 and W1, the chain construction
  and verification logic is sound: each entry binds to the previous, the genesis
  entry has `previous_hash = ""`, and `verify_chain` walks chronologically.
- **`@guarded` decorator dispatches on async vs sync** based on
  `asyncio.iscoroutinefunction(func)` and preserves `__name__` via `functools.wraps`
  in every wrapper.
- **CLI tests use Typer's `CliRunner`** with a per-test `tmp_path` `chdir` — clean,
  no DB pollution between tests.

---

## Verdict

**NEEDS FIXES** — do not publish 0.1.0 to PyPI in the current state.

There are three blocking concerns and one near-blocker:

1. **C1 (broken templates / CLI `--name`)** — every user following the README hits this on
   the first `register` command. This alone is publication-blocking.
2. **C3 (broken doc imports)** — every user trying the LangChain or CrewAI quickstart
   crashes immediately. Publication-blocking for the headlined integrations.
3. **C2 (duplicate hash function)** — not user-facing today, but it is a security-critical
   booby-trap waiting for the next refactor. Must be cleaned up before 0.1.0 is frozen,
   because audit DBs created against 0.1.0 will need to validate against 0.1.1+ forever.
4. **C4 (audit-chain race under concurrency)** — the entire tamper-evidence value-prop
   silently degrades the moment two coroutines log in parallel. Either fix it or document
   the limitation prominently and add an `asyncio.Lock` follow-up issue.

After C1–C4 are fixed and W1–W3 (the security-relevant test gaps) are filled, the
codebase is in good shape: architecture is clean, tests are real, threat model is
consistent, and packaging is mostly there. With the metadata polish in S7, this
becomes a credible 0.1.0 release.

Recommended path:

1. Patch C1 (≤20 LoC) + add a CLI test with the actual templates.
2. Patch C3 (re-export or doc-fix; ≤10 LoC).
3. Patch C2 (delete dead code; ≤15 LoC) + pin the hash format with a unit test.
4. Patch C4 (`asyncio.Lock` or `BEGIN IMMEDIATE`) + concurrent-log_audit test.
5. Fix W1–W3 test gaps.
6. Run `ruff --fix` for the 15 auto-fixable lint errors.
7. Polish `pyproject.toml` (S7).
8. Tag 0.1.0 and publish.
