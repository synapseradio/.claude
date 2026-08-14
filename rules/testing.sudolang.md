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

A test earns trust by failing once, for a reason its message names. What
follows covers what makes a test worth keeping, how much of the suite runs,
and how a test stays sealed off from real user state and its surroundings.

Testing {
  Applies { writing, changing, or judging tests }
    // the test itself
    via(WritingCode.ImplementFlow)  // decides when a test gets written

  Worth {
    Constraints {
      a test carries value only when its expected result comes from
        somewhere other than the code it checks
        // the oracle stands outside the system under test
      each test fails for one reason, and its failure message says which
      the verdict holds across identical runs  // tolerate no flake:
                                               // fix the test or delete it
      never trust a test you have not seen fail for the right reason
        // FunctionShadowing is one instance of this
      a recorded reason makes an untested claim a decision, and no record
        leaves it a gap
    }
  }

  RunScope {
    run only the tests covering changed files, mapping source to test by
      convention
    (the user asks | the scope warrants it | no narrower mapping exists) =>
      the full suite runs
    (the project carries a "test changed files" tool) => use it
  }

  Names {
    name a test for the behavior it describes:
      `<subject> <verb> <behavior> [when <condition>]`
    a failing test reads as a sentence
  }

  Assertions {
    use the framework's assertion library
    never write ad-hoc checks that discard context on failure
  }

  ScopeTags {
    // tag tests by what they touch, wherever the framework supports tags
    // or filename conventions
    smoke       { does it load and respond? }
    unit        { one isolated function or module, with no I/O }
    integration { cross-module flow with controlled fixtures }
    tag-based filtering gives fast feedback during development
  }

  Isolation {
    require tests never touch real user state
    require no test runs `rm -rf` against a resolved production path

    fn setup() {
      create a temporary directory, and export an override env var
        pointing at it before sourcing the system under test
    }
    fn teardown() {
      remove the temp dir, targeting the variable that holds it
    }

    Constraints {
      never depend on test order, working directory, or the user's
        environment
    }
  }

  Mocks {
    Constraints {
      mock at the boundary rather than in the middle
      (a CLI invokes external commands) => mock executables in a temp dir
        on `$PATH`
      (a library calls I/O or the network) => inject the dependency or use
        the framework's mocking primitive
        // never monkey-patch globals from inside a test
      note the version of the real interface the mock was written against
        // a mock that drifts from reality does more harm than no mock
    }
  }

  FunctionShadowing {
    (the project defines a function shadowing a test framework function) =>
      never assume a test passes meaningfully without first verifying that
      it fails for the right reason
  }
}
