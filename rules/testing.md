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

We value a test whose green means the code is right and whose red says why. An expected result derived from the code under test proves the code agrees with itself, and a green nobody watched fail proves nothing, so the expectation comes from elsewhere and the failure gets seen first. A test that touches real user state or depends on order, working directory, or the user's environment destroys data or flakes, so a bash test creates a temporary directory and exports an override env var pointing at it before sourcing the system under test, removing it in teardown through that variable. A claim left untested gets its reason recorded, so the gap reads as a decision.

```sudolang
Test {
  name: "<subject> <verb> <behavior> [when <condition>]", so a failure reads as a sentence
  tag: smoke | unit | integration, by what the test touches, in a framework that tags
  expected: from somewhere other than the code under test
  assertion: the framework's assertion library
}

fn write(test) {
  each test fails for one reason, its message says which
  mock = kind => match (kind) {
    case CLI => executables in a temp dir on `$PATH`
    case I/O or network => an injected dependency or the framework's primitive
  }
  note the version of the real interface each mock was written against
  a claim stays untested => record why
}

run = scope => match (scope) {
  case the user asks, the scope warrants it, or no narrower mapping exists => the full suite
  default => only tests covering changed files, mapped by convention or the project's
    own "test changed files" tool
}

fn judge(result) {
  trust a green only after watching it fail for the right reason
  the project shadows a framework function => a pass means nothing until you have
    watched it fail
  the verdict differs across identical runs => fix the flake or delete the test
}

require no test touches real user state
require no test runs rm -rf against a resolved production path
require no test depends on order, working directory, or the user's environment
require never a monkey-patched global from inside a test
require never an ad-hoc check that discards context on failure
```
