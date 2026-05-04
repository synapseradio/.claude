# Testing

Applies whenever tests are read, written, or run.

## When tests fail (or hang, or lint, or hook-block)

A red signal is the contract speaking, not a status report. The moment any deterministic check fires red — failing test, hung test, lint error, commit-hook block, build break — stop the original work and create one `TaskCreate` per red item. Investigate. Fix. Then resume. No commit, no push, no "done" claim, no asking the user to bless deferral until the suite is green again.

The label "pre-existing" is irrelevant — a test red for six months is still red right now. The label "unrelated" is irrelevant — your job is the suite, not just your diff. The phrase "out of scope" does not apply to red signals; they expand scope automatically. This is the explicit exception to scope-discipline (Core Rule 12 and the operating rule on deterministic failure signals).

Defer only with explicit per-failure user authorization, requested individually with the concrete reason for that one failure. Never bundle. Never assume.

## Run scope

- Never run the full test suite by default. Run only the tests covering files you changed. Map source → test (e.g., `lib/foo.sh` → `tests/foo.bats`, `src/Foo.ts` → `src/Foo.test.ts`, `pkg/foo.go` → `pkg/foo_test.go`). The full suite runs only when the user asks, the scope warrants it (release prep, suspected systemic regression), or no narrower mapping exists.
- If the project provides a "test the changed files" tool (e.g., a `test-changed` script, a watcher with focused mode), use it.

## think about and write failing tests before any behavioral change.

When modifying behavior, write the failing test before changing the code. Run it to confirm it fails for the right reason — the absence of the new behavior, not a syntax error or missing import. A test that passes immediately wasn't proving anything.

## Scope tags

Tag tests by what they touch, when the framework supports tags or filename conventions:

- **smoke** — does it load and respond at all?
- **unit** — one isolated function or module, no I/O
- **integration** — cross-module flow with controlled fixtures

Use tag-based filtering for fast feedback during development.

## Names

Use behavior-description names: `<subject> <verb> <behavior> [when <condition>]`. Avoid framework-meta names like `test_function_1` or `should work`. A failing test should read like a sentence: "parser rejects trailing comma when strict mode."

## Assertions

Always use the framework's assertion library — never raw `[ ]`, hand-rolled `if` checks, or bare `assert x ==` that throws away context on failure. The assertion library exists for the failure message; raw checks discard it.

## Test isolation

Tests must never touch real user state.

- Setup creates a temporary directory; teardown removes it.
- Always export an override env var (e.g., `XDG_*_HOME`, project-specific `*_DIR`) pointing at the temp dir before sourcing or initializing the system under test.
- `rm -rf "$TMPDIR_VAR"`, never `rm -rf "$RESOLVED_PRODUCTION_PATH"`. If the system under test reads config that *overwrites* your override, that is a test-isolation bug — find and fix the config-read order before continuing.
- Do not depend on the order tests run, the working directory, or the user's environment.

## Mocks

Mock at the boundary, not in the middle.

- For CLIs invoking external commands: place mock executables in a temp dir on `$PATH`.
- For libraries calling I/O or network: inject the dependency, or use the framework's mocking primitive — don't monkey-patch globals from inside a test.
- A mock that drifts from the real interface is worse than no mock. Note the version of the real thing the mock was written against.

## Function shadowing

If the project defines a function with the same name as one the test framework provides (e.g., `fail`, `error`, `assert`, `mock`), assertions and helpers may silently no-op. Verify a new test fails for the right reason before assuming a passing test is meaningful.
