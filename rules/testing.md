---
paths:
  - "**/*.{test,spec}.*"
  - "**/*{_test,_spec,Test,Tests,Spec,Specs}.*"
  - "**/test_*.*"
  - "**/*bats*"
  - "**/{__tests__,__mocks__,__fixtures__,tests,test,spec,specs,e2e,cypress,playwright,integration,testdata,fixtures}/**"
  - "**/*.{feature,test}"
---

<!-- rule: testing -->

## testing

For every test you write, change, or judge, optimize for a test whose description records an intention and whose green shows that intention still holds, whatever has changed since.

Read a test suite as living documentation of what was built and for whom. Before writing a test, name the person it serves, a user of a UI or an engineer writing a caller, what they are trying to do, and the experience intended for them. Write the test for their ease and for the maintainer's clarity.

Let each test fail for one reason, with a message that says which.

Where the user asks, the scope warrants it, or no narrower mapping exists, run the full suite. Otherwise, run only the tests covering changed files, mapped by convention or the project's own tool for changed files.
