# Testing

<when> tests are read, written, or run.

## When tests fail

<never> Commit, push, or claim "done" while any deterministic check is red — failing test, hung test, lint error, commit-hook block, build break.
<prefer> The failure becomes the next task. See Core Rule 12 and [operating-rules.md](./operating-rules.md).

<never> Dismiss a red test as "pre-existing", "out of scope", or "unrelated." A test red for six months is still red.

<never> Defer a failure without explicit per-failure user authorization. Never bundle. Never assume.

## Run scope

<prefer> Run only tests covering changed files. Map source → test (e.g., `lib/foo.sh` → `tests/foo.bats`, `src/Foo.ts` → `src/Foo.test.ts`). The full suite runs only when the user asks, the scope warrants it, or no narrower mapping exists.
<prefer> If the project has a "test changed files" tool, use it.

## Write failing tests before behavioral change

<prefer> When modifying behavior, update the test before changing code. Run it to confirm it fails for the right reason — the absence of the new behavior, not a syntax error or missing import. A test that passes immediately proves nothing.

## Scope tags

<prefer> Tag tests by what they touch, when the framework supports tags or filename conventions:
- **smoke** — does it load and respond?
- **unit** — one isolated function or module, no I/O
- **integration** — cross-module flow with controlled fixtures

<prefer> Use tag-based filtering for fast feedback during development.

## Names

<prefer> Behavior-description names: `<subject> <verb> <behavior> [when <condition>]`. A failing test should read as a sentence: "parser rejects trailing comma when strict mode." Avoid names like `test_function_1` or `should work`.

## Assertions

<never> Use raw `[ ]`, hand-rolled `if` checks, or bare `assert x ==` that discards context on failure.
<prefer> Use the framework's assertion library.

## Test isolation

<never> Touch real user state.

<always> Setup creates a temporary directory. Teardown removes it.
<always> Export an override env var (e.g., `XDG_*_HOME`) pointing at the temp dir before sourcing the system under test.
<always> `rm -rf "$TMPDIR_VAR"`, never `rm -rf "$RESOLVED_PRODUCTION_PATH"`.
<always> Do not depend on test order, working directory, or the user's environment.

## Mocks

<always> Mock at the boundary, not in the middle.

<prefer> For CLIs invoking external commands: place mock executables in a temp dir on `$PATH`.
<prefer> For libraries calling I/O or network: inject the dependency, or use the framework's mocking primitive. Do not monkey-patch globals from inside a test.
<prefer> Note the version of the real interface the mock was written against. A mock that drifts from reality is worse than no mock.

## Function shadowing

<never> Assume a test passes meaningfully without verifying it first fails for the right reason, when the project defines a function that shadows a test framework function (e.g., `fail`, `error`, `assert`, `mock`).
