---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.mjs"
  - "**/*.cjs"
  - "**/*.py"
  - "**/*.go"
  - "**/*.rs"
  - "**/*.rb"
  - "**/*.java"
  - "**/*.kt"
  - "**/*.swift"
  - "**/*.c"
  - "**/*.cc"
  - "**/*.cpp"
  - "**/*.cxx"
  - "**/*.h"
  - "**/*.hpp"
  - "**/*.cs"
  - "**/*.php"
  - "**/*.scala"
  - "**/*.clj"
  - "**/*.ex"
  - "**/*.exs"
  - "**/*.erl"
  - "**/*.lua"
  - "**/*.zig"
  - "**/*.nim"
  - "**/*.dart"
  - "**/*.elm"
  - "**/*.hs"
  - "**/*.ml"
  - "**/*.fs"
  - "**/*.r"
---

# How to Implement

Applies when implementing a new feature, fixing a bug, or adding new behavior.

Follow the scientific method. Every implementation is an experiment: form a hypothesis (the test), run the experiment (the code), observe the result.

1. **Understand the requirement.** If the acceptance criteria are unclear, ask before writing anything.
2. **Write a failing test first.** The test encodes the expected behavior. Run it to confirm it fails for the right reason — not a syntax error or missing import, but the absence of the behavior you're about to implement.
3. **Implement the minimum code to pass.** No more. Resist the urge to handle edge cases, add configurability, or refactor adjacent code in the same step.
4. **Run the test to confirm it passes.** If it doesn't, the implementation is wrong — not the test. Fix the code, not the expectation, unless the requirement was misunderstood (go back to step 1).
5. **Refactor if needed, re-run after each change.** Keep behavior changes and structural changes in separate steps.

If the project has no test infrastructure, flag it before writing code — don't skip testing.

When modifying existing behavior, update the test first. The failing test proves the old behavior exists and the new behavior doesn't — yet.

Run only the tests affected by your changes, never the full suite, unless asked or the scope warrants it.
