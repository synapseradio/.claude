# Testing

When tests are read, written, or run.

## Run scope

Run only tests covering changed files. Map source to test by convention. The full suite runs only when the user asks, the scope warrants it, or no narrower mapping exists.

If the project has a "test changed files" tool, use it.

## Write failing tests before behavioral change

When modifying behavior, update the test before changing the code. Run it to confirm it fails for the right reason: the absence of the new behavior. A test that passes immediately proves nothing.

## Scope tags

Tag tests by what they touch, when the framework supports tags or filename conventions:

- **smoke** — does it load and respond?
- **unit** — one isolated function or module, no I/O
- **integration** — cross-module flow with controlled fixtures

Use tag-based filtering for fast feedback during development.

## Names

Use behavior-description names following the pattern `<subject> <verb> <behavior> [when <condition>]`. A failing test should read as a sentence.

## Assertions

Use the framework's assertion library. Never write ad-hoc checks that discard context on failure.

## Test isolation

Never touch real user state.

Setup creates a temporary directory. Teardown removes it.

Export an override env var pointing at the temp dir before sourcing the system under test.

When removing the temp dir, target the variable that holds it. Never `rm -rf` a resolved production path.

Do not depend on test order, working directory, or the user's environment.

## Mocks

Mock at the boundary, not in the middle.

For CLIs invoking external commands, place mock executables in a temp dir on `$PATH`.

For libraries calling I/O or network, inject the dependency or use the framework's mocking primitive. Do not monkey-patch globals from inside a test.

Note the version of the real interface the mock was written against. A mock that drifts from reality is worse than no mock.

## Function shadowing

When the project defines a function that shadows a test framework function, never assume a test passes meaningfully without first verifying it fails for the right reason.
