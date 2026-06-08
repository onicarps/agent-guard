# Factory Mission 3: Full Codebase Audit

## Project Context

Agent-Guard v0.1.0 is an "IAM for AI Agents" Python library. Workspace: `/home/oni/.hermes/profiles/agent-guard/workspace/`

Current state: 73 tests pass (1 xfail), 98% coverage. All features implemented. About to publish to PyPI.

## Your Mission

Conduct a THOROUGH audit of the entire codebase. Read every source file, test file, config file, and doc. Then produce a structured audit report.

## What to Audit

### 1. Code Quality & Correctness

Read every file in `src/agent_guard/` and check for:

- **Logic bugs**: Are there edge cases that produce wrong results? (e.g., permission checks that should deny but allow, or vice versa)
- **Error handling**: Are all error paths handled? What happens with corrupted DB, missing files, invalid input?
- **Type safety**: Are there any `Any` types that should be more specific? Missing type hints?
- **Import issues**: Any circular imports? Unused imports? Missing imports?
- **Naming consistency**: Are function/variable names consistent across modules?
- **Dead code**: Any unreachable code, unused functions, or commented-out code?
- **Security issues**: SQL injection, path traversal, secret leakage, unsafe deserialization?

### 2. Test Quality

Read every test file and check for:

- **Coverage gaps**: What's NOT tested? (the 2% missing — lines 38-40 in custom.py, line 139 in cli.py, lines 81/85-86 in policies.py, lines 140/217 in registry.py)
- **Test correctness**: Do tests actually test what they claim? Any tests that pass for the wrong reason?
- **Edge cases**: Are boundary conditions tested? (empty strings, None values, max integers, concurrent access)
- **Test isolation**: Do tests properly clean up? Any shared state between tests?
- **Fixture quality**: Are fixtures reusable and well-structured?

### 3. Architecture & Design

- **Module boundaries**: Is each module focused on a single responsibility?
- **API design**: Are the public APIs intuitive? Would a developer know how to use this?
- **Extensibility**: How easy is it to add new resource types, new integrations, new storage backends?
- **Dependency graph**: Are dependencies minimal and well-chosen?

### 4. Documentation Accuracy

Read `docs/usage.md` and `docs/security.md` and verify:

- Do code examples actually work? (Try to mentally execute them)
- Are all public APIs documented?
- Are there documented features that don't exist?
- Are there undocumented features that should be documented?
- Is the threat model accurate?

### 5. Configuration & Packaging

Read `pyproject.toml` and check:

- Are all dependencies listed? (direct and transitive)
- Are version constraints appropriate?
- Is the entry point correct?
- Are optional dependencies properly grouped?
- Is the metadata accurate (name, version, description, license)?

### 6. Template Validation

Read all YAML templates in `templates/` and verify:

- Do they parse correctly with `yaml.safe_load()`?
- Does the parsed output pass `AgentPolicy(**data)` validation?
- Are the `{{name}}` placeholders handled correctly by the CLI?

## Output Format

Produce a structured report with these sections:

### Critical Issues (must fix before publish)
List any bugs, security vulnerabilities, or broken functionality. Include file paths and line numbers.

### Warnings (should fix before publish)
List any code quality issues, missing error handling, or potential runtime failures.

### Suggestions (nice to fix)
List any improvements to code quality, test coverage, or documentation.

### Positive Findings
List what's well-done. This is important — acknowledge good work.

### Verdict
**READY TO PUBLISH** / **NEEDS FIXES** — your recommendation.

## Important Notes

- Do NOT modify any files — this is a read-only audit
- Be specific: include file paths, line numbers, and exact descriptions
- If you find a bug, describe the exact input that triggers it
- If a test is missing, describe what scenario it should cover
- Check the actual code, not just the documentation
