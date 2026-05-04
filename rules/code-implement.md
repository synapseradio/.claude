# How to Implement

<when> implementing a new feature, fixing a bug, or adding new behavior.

<prefer> 1. Understand the requirement. If acceptance criteria are unclear, ask before writing anything.
<prefer> 2. Write a failing test. Run it to confirm it fails for the right reason — the absence of the behavior, not a syntax error or missing import.
<prefer> 3. Implement the minimum code to pass the test. No edge cases, no configurability, no refactoring adjacent code in this step.
<prefer> 4. Run the test. If it does not pass, fix the code. Do not change the test unless the requirement was misunderstood — go back to step 1.
<prefer> 5. Refactor if needed. Re-run after each change. Keep behavior and structure changes separate.

<never> Skip testing because no test infrastructure exists.
<prefer> Flag the gap before writing code.

<never> Run the full test suite by default.
<prefer> Run only tests covering changed files. See [testing.md](./testing.md).
