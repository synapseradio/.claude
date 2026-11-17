## writing-tests

For every test you write, change, remove, run, or judge, optimize for a suite of few tests, each failing only when a behavior a person relies on breaks.

- story: an outcome a person gets, with the acceptance lines that show it
- exposed interface: a surface that code or people outside a module call or read and that its owner promises to keep, a public API, a module's entry point, a command's flags and exit codes, a route, a file format, or a documented guarantee for one
- internal: everything behind an exposed interface

### Which tests

Take every expected value from a source outside the code under test, a story, a spec, a decision, or an example worked by hand.
Sort each behavior, taking the first arm that fits.

choose behavior
  | an existing test fails when it breaks = write none
  | a story states it
      = one test for the story, driven the way its person drives the subject, asserting its acceptance lines, named for what that person observes
  | it is a promise at an exposed interface = one contract test through that interface, asserting only the promise
  | otherwise, it is internal = write none

Give a story a second test only for a starting state the first cannot reach, and an edge a test only where an acceptance line or a documented promise names it.
Write a test before or after its source, in the order the plan gives.
A test would have to exercise a branch for a state that should never happen ? strengthen the type until the branch disappears, and write a test guarding the invariant only where that type was declined.

Before writing a test, put four questions to it:

1. Would it fail under a restructuring that keeps every outcome a person observes and every promise of the interface?
2. Does its expected value come from the code under test, a copied constant, the source's own formula, or a snapshot of internals for one?
3. Does every wrong implementation that fails it also fail another test?
4. Do its assertions read stand-ins for collaborators the subject owns, in place of an outcome?

A yes to any ? raise the test to the outcome or the promise, or leave it unwritten.

### Inside a test

A test would assert behavior suspected wrong and still undecided ? write it as a todo test, `it.todo()` for one, its intended assertion commented out beneath a block comment stating the mechanism, the stake for whoever uses the product, and the options unranked. Keep schedule, ticket, and owner out of that comment. Keep every green assertion on a suspected defect out of a suite, one beside a hazard comment included.
A comment would say why a test asserts what it does ? write it in the test as the rationale, linking a page per browser, framework, or library behavior the assertion assumes. That comment may describe code outside the test's file, naming the behavior under test the assertion rests on.
A test for an invariant lands in a later change ? write a TODO in the source naming the test by its description, plus an owner or ticket, leaving the assertion to the test.
A docstring would state a property a test asserts ? leave the property to the test.

### Judging

Judge an existing test by reading it. Direct every delegate that judges tests to judge them by reading them.
Keep mutation checks out of the work and every prompt and brief: deliberately broken code, scratch mutants, and failing assertions added to watch a suite go red.

### Runs

Treat a test count, total or passing, as no evidence a change is safe and as no acceptance criterion. Name the property a change promises -> check that property directly.
A test fails on a branch with changes ? hold the branch as its cause -> find the change that caused it and fix it, with runs on the base and the word "unattributed" kept out.
A run reports no tests found ? count it as a miss, its exit code as no ground for a pass -> run the suite through the runner its own package declares.
A change edits only comment text, JSDoc included ? commit it with no test run.
Run a test suite against each commit of a branch in a plain shell, looping over `git checkout --detach <sha>` with `GIT_DIR` and `GIT_WORK_TREE` unset, with every test run kept out of `git rebase --exec`.

### Boundaries

Mock GraphQL at the network boundary, MSW for one, in place of module mocks of the query hook or the store it feeds.
Test each repository's behavior in its own suite alone, with a sibling repository's paths, CLI, and installed copies kept out of every test. Keep each of two isolated repositories' paths and tools out of the other's code and commits.
A test sources code that would load a sibling repository ? point that loader at a missing path, so the result holds whether the sibling is installed or not.
