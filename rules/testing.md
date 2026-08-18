---
paths:
  - "**/*.{test,spec}.*"
  - "**/*{_test,_spec,Test,Tests,Spec,Specs}.*"
  - "**/test_*.*"
  - "**/*bats*"
  - "**/{__tests__,__mocks__,__fixtures__,tests,test,spec,specs,e2e,cypress,playwright,integration,testdata,fixtures}/**"
  - "**/*.{feature,test}"
---

Testing {
  AppliesWhen { writing, changing, or judging a test }

  constraint Worth {
    require the expected result comes from somewhere other than the code
      under test
    require each test fails for one reason, and its message says which
    require the verdict holds across identical runs: fix a flaking test or
      delete it
    require you have watched a test fail for the right reason before you
      trust it green, and treat a pass as meaningless until then where the
      project shadows a framework function
    (a claim stays untested) => record why, so the gap reads as a decision
  }

  constraint RunScope {
    run only the tests covering changed files, mapped by convention or by
      the project's own "test changed files" tool
    (the user asks || the scope warrants it || no narrower mapping exists)
      => run the full suite
  }

  constraint Names {
    name each test `<subject> <verb> <behavior> [when <condition>]`, so a
      failure reads as a sentence
    tag each test by what it touches where the framework supports it:
      smoke | unit | integration
  }

  constraint Assertions {
    use the framework's assertion library, never an ad-hoc check that
      discards context on failure
  }

  constraint Isolation {
    require no test touches real user state, and none runs `rm -rf` against
      a resolved production path
    create a temporary directory and export an override env var pointing at
      it before sourcing the system under test, and remove it in teardown
      through that variable
    require no test depends on order, working directory, or the user's
      environment
  }

  constraint Mocks {
    mock at the boundary: executables in a temp dir on `$PATH` for a CLI,
      an injected dependency or the framework's primitive for I/O and
      network, never a monkey-patched global from inside a test
    note the version of the real interface each mock was written against
  }
}
