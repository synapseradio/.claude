# How to Implement

When adding or modifying behavior.

1. Understand the requirement. If acceptance criteria lack clarity, ask before writing anything.
2. Write a failing test and run it, following [tdd.md](./tdd.md), which owns the method.
3. Implement the minimum code to pass the test. Nothing else.
4. Run the test. If it does not pass, fix the code. Do not change the test unless the requirement was misunderstood — go back to step 1.
5. Refactor if needed. Re-run after each change. Keep behavior and structure changes separate.

Never skip testing because no test infrastructure exists. Flag the gap before writing code.
