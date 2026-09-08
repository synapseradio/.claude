---
paths:
  - "**/*.{test,spec}.*"
  - "**/*{_test,_spec,Test,Tests,Spec,Specs}.*"
  - "**/test_*.*"
  - "**/*bats*"
  - "**/{__tests__,__mocks__,__fixtures__,tests,test,spec,specs,e2e,cypress,playwright,integration,testdata,fixtures}/**"
  - "**/*.{feature,test}"
---

<rule name="testing">

  <applies_when>
    You are writing, changing, or judging a test.
  </applies_when>

  <optimize_for>
    a test whose green means the code is right and whose red says why.
    <why_it_matters>
      An expectation derived from the code proves only that the code agrees with itself. A green nobody watched fail proves nothing. A test that touches real user state or depends on order, working directory, or the user's environment destroys data or flakes. A recorded reason makes an untested claim read as a decision.
    </why_it_matters>
  </optimize_for>

  <define name="test">
    A test's name takes the form `<subject> <verb> <behavior> [when <condition>]`. Its tag is smoke, unit, or integration, by what it touches, in a framework that tags. Its expected result comes from somewhere other than the code under test. Its assertions come from the framework's assertion library.
  </define>

  <do name="write">
    Let each test fail for one reason, with a message that says which. Mock a CLI with executables in a temporary directory on `$PATH`. Mock I/O or the network with an injected dependency or the framework's primitive. Note the version of the real interface each mock was written against. Where a claim stays untested, record why.
  </do>

  <do name="bash">
    In a bash test, create a temporary directory and export an override env var pointing at it before sourcing the system under test. Remove the directory in teardown through that variable.
  </do>

  <decide name="run">
    Where the user asks, the scope warrants it, or no narrower mapping exists, run the full suite. Otherwise, run only the tests covering changed files, mapped by convention or the project's own tool for changed files.
  </decide>

  <do name="judge">
    Trust a green only after watching it fail for the right reason. Where the project shadows a framework function, a pass means nothing until you have watched it fail. Where the verdict differs across identical runs, fix the flake or delete the test.
  </do>

  <require>
    Never let a test touch real user state. Never let a test run rm -rf against a resolved production path. Never let a test depend on order, working directory, or the user's environment. Never monkey-patch a global from inside a test. Never write an ad-hoc check that discards context on failure.
  </require>

</rule>
