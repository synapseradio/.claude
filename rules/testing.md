---
paths:
  - "**/*.{test,spec}.*"
  - "**/*{_test,_spec,Test,Tests,Spec,Specs}.*"
  - "**/test_*.*"
  - "**/*bats*"
  - "**/{__tests__,__mocks__,__fixtures__,tests,test,spec,specs,e2e,cypress,playwright,integration,testdata,fixtures}/**"
  - "**/*.{feature,test}"
---

# Testing

This applies when writing, changing, or judging a test.

## Worth

The expected result comes from somewhere other than the code under test. Each test fails for one reason, and its message says which. The verdict holds across identical runs: fix a flaking test or delete it. Trust a test green only after you have watched it fail for the right reason, and where the project shadows a framework function, treat a pass as meaningless until then. When a claim stays untested, record why, so the gap reads as a decision.

## Run scope

Run only the tests covering changed files, mapped by convention or by the project's own "test changed files" tool. When the user asks, the scope warrants it, or no narrower mapping exists, run the full suite.

## Names and assertions

Name each test `<subject> <verb> <behavior> [when <condition>]`, so a failure reads as a sentence. Tag each test by what it touches where the framework supports it: smoke, unit, or integration. Use the framework's assertion library, never an ad-hoc check that discards context on failure.

## Isolation

No test touches real user state, and none runs `rm -rf` against a resolved production path. Create a temporary directory and export an override env var pointing at it before sourcing the system under test, and remove it in teardown through that variable. No test depends on order, working directory, or the user's environment.

## Mocks

Mock at the boundary: executables in a temp dir on `$PATH` for a CLI, an injected dependency or the framework's primitive for I/O and network, never a monkey-patched global from inside a test. Note the version of the real interface each mock was written against.
