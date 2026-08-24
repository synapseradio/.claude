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

```sudolang
Constraints {
  the expected result comes from somewhere other than the code under test
  each test fails for one reason, and its message says which
  the verdict holds across identical runs: fix a flaking test or delete it
  trust a green only after watching it fail for the right reason;
    the project shadows a framework function => a pass means nothing until then
  a claim stays untested => record why, so the gap reads as a decision
}
```

## Run scope

```sudolang
runScope = match {
  the user asks, the scope warrants it, or no narrower mapping exists => the full suite
  default => only tests covering changed files, mapped by convention
    or the project's own "test changed files" tool
}
```

## Names and assertions

```sudolang
testName = "<subject> <verb> <behavior> [when <condition>]",
  so a failure reads as a sentence
tag each test by what it touches where the framework supports it:
  smoke | unit | integration
use the framework's assertion library, never an ad-hoc check
  that discards context on failure
```

## Isolation

```sudolang
Constraints {
  require no test touches real user state, and none runs rm -rf against
    a resolved production path
  create a temporary directory and export an override env var pointing at it
    before sourcing the system under test, removing it in teardown through that variable
  no test depends on order, working directory, or the user's environment
}
```

## Mocks

```sudolang
mockAtTheBoundary = match (kind) {
  CLI => executables in a temp dir on $PATH
  I/O or network => an injected dependency or the framework's primitive
}
never a monkey-patched global from inside a test
note the version of the real interface each mock was written against
```
