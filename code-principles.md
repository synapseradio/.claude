<!-- @-referenced from CLAUDE.md — loaded when coding tasks are active -->

## How to Write Code

### Simplicity over cleverness

Choose the approach with fewer moving parts, fewer dependencies, and fewer assumptions. Simple is not the same as easy — prefer unfamiliar-but-straightforward over familiar-but-tangled.

Context: You're applying logic to a collection of data.
Do this: a plain loop that's readable in 10 seconds.
Not this: a clever chain of higher-order functions that takes 2 minutes to trace.

### Work incrementally

Break large changes into the smallest working steps. Complete each step before starting the next. The order is: make it clear, make it work, make it right, make it fast. In that order, and never at the same time.

Keep structural cleanup (renaming, reordering, extracting) separate from behavior changes. Never mix refactoring with feature work in the same edit. Separate them with hunks / commits and tasks on your list.

A complex system that works was always evolved from a simple system that worked. Start simple. Grow incrementally. Never design a complex system from scratch.

### Duplication over wrong abstraction

Do not deduplicate code unless the duplicated pieces truly represent the same concept and change for the same reasons. If shared code has conditional branches to handle different callers, that abstraction is wrong — inline it and tolerate the duplication.

Wrong abstractions create coupling that is far more expensive to remove than duplication is to maintain.

Do this: two similar-looking functions that serve different purposes.
Not that: one "flexible" function with boolean flags controlling which path it takes.

### Optimize for change

Code is modified far more often than it is written. When designing a function, module, or API, ask: "how will someone change this next?" Make the likely next change easy. Readable and changeable beats elegant and rigid.

### Clarity is mandatory

Write code that reveals intent to a reader with no prior context. Names describe what something represents, not how it's implemented. Comments explain why, never what — the code shows the what.

If a function needs a comment to explain what it does, rename it. If a block of logic is hard to follow, extract it into a well-named function.

Do this: `getActiveUsersByTeam(teamId)`
Not that: `process(id, true, null)` with a comment explaining what the arguments mean.

### Make invalid states impossible

Design types and data structures so illegal combinations cannot be constructed. Prefer enums over boolean flags. Prefer required fields over optional-with-defaults. If a value must be one of three things, make the type enforce that constraint.

Do this: `status: 'draft' | 'published' | 'archived'`
Not that: `isDraft: boolean, isPublished: boolean` where both could be true.

### Predict before executing

Before running code or tests, state what you expect to happen. When debugging, articulate the hypothesis before changing anything. If you have multiple hypotheses, find a test that distinguishes them before making changes.

Do not change code to "see what happens." Change code because you believe it will produce a specific result, and then verify.

### Deep modules, simple interfaces

Give functions and modules simple interfaces that hide internal complexity. The caller should not need to understand the implementation. A 3-parameter function that does significant work is better than a 10-parameter function that does a little.

## Language-Specific References

### Bash / Shell Scripts

**MANDATORY**: When writing, reviewing, or modifying any Bash or shell script (`.sh`, `.bash`, or shebang `#!/bin/bash`/`#!/bin/sh`), load and follow the full style guide at:

`~/.claude/bash-style-guide.md`

Key conventions: `snake_case` for functions and variables, `function` keyword, `readonly` / `local` where appropriate, `[[ ]]` over `[ ]`, proper error handling, POSIX compatibility where noted. The reference contains every rule — read it, don't rely on memory.
