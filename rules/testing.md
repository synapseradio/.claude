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
  - "**/*bats*"
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
  - "**/integration/**"
  - "**/testdata/**"
  - "**/fixtures/**"
  - "**/*.feature"
  - "**/*.test"
---

# Testing

```sudolang
Testing {
  Applies { writing, changing, or judging tests }
    // ImplementFlow in ./writing-code.md decides when a test gets
    // written; this file governs the test itself

  Worth {
    a test carries value only when its expected result comes from somewhere
      other than the code it checks
      // the oracle stands outside the system under test
    each test fails for one reason, and its failure message says which
    the verdict holds across identical runs  // flake forbids nothing
    never trust a test you have not seen fail for the right reason
      // FunctionShadowing below is one instance of this
    an untested claim with a recorded reason is a decision;
      one with no record is a gap
  }

  RunScope {
    run only tests covering changed files; map source to test by convention
    the full suite runs only when the user asks, the scope warrants it,
      or no narrower mapping exists
    the project has a "test changed files" tool -> use it
  }

  Names {
    behavior-description names: `<subject> <verb> <behavior> [when <condition>]`
    a failing test reads as a sentence
  }

  Assertions {
    use the framework's assertion library
    never ad-hoc checks that discard context on failure
  }

  ScopeTags {
    // tag tests by what they touch, when the framework supports tags
    // or filename conventions
    smoke       { does it load and respond? }
    unit        { one isolated function or module, with no I/O }
    integration { cross-module flow with controlled fixtures }
    tag-based filtering -> fast feedback during development
  }

  Isolation {
    never touch real user state
    setup creates a temporary directory; teardown removes it
    export an override env var pointing at the temp dir
      before sourcing the system under test
    removing the temp dir -> target the variable that holds it;
      never `rm -rf` a resolved production path
    never depend on test order, working directory, or the user's environment
  }

  Mocks {
    mock at the boundary, not in the middle
    a CLI invoking external commands -> mock executables in a temp dir on `$PATH`
    a library calling I/O or network -> inject the dependency, or use the
      framework's mocking primitive
      // never monkey-patch globals from inside a test
    note the version of the real interface the mock was written against
      // a mock that drifts from reality does more harm than no mock
  }

  FunctionShadowing {
    the project defines a function shadowing a test framework function
      -> never assume a test passes meaningfully without first verifying
         it fails for the right reason
  }
}
```
