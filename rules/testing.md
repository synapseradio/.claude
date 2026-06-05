---
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "**/*_test.*"
  - "**/*_spec.*"
  - "**/test_*.*"
  - "**/*Test.*"
  - "**/*Tests.*"
  - "**/*Spec.*"
  - "**/*Specs.*"
  - "**/*.bats"
  - "**/__tests__/**"
  - "**/__mocks__/**"
  - "**/__fixtures__/**"
  - "**/tests/**"
  - "**/test/**"
  - "**/spec/**"
  - "**/specs/**"
  - "**/e2e/**"
  - "**/cypress/**"
  - "**/playwright/**"
  - "**/integration-tests/**"
  - "**/integration_tests/**"
  - "**/testdata/**"
  - "**/fixtures/**"
  - "**/*.feature"
  - "**/*.test"
---

# Testing

When tests are read, written, or run.

## Run scope

Run only tests covering changed files. Map source to test by convention. The full suite runs only when the user asks, the scope warrants it, or no narrower mapping exists.

If the project has a "test changed files" tool, use it.

## Names

Use behavior-description names following the pattern `<subject> <verb> <behavior> [when <condition>]`. A failing test should read as a sentence.

## Assertions

Use the framework's assertion library. Never write ad-hoc checks that discard context on failure.

## Patterns

For scope tags, test isolation, mocks, and function shadowing, see [../references/testing-patterns.md](../references/testing-patterns.md).
