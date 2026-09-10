<!-- rule: writing-code -->

## writing-code

For all source code you write or modify, optimize for code whose behavior a test asserted before the code existed, and whose next change is easy.

### The test-first loop

Find the boundaries and invariants first. Ask wherever an acceptance criterion is unclear. Predict the failures before modifying code. Then repeat this loop. Write the isolated failing test, run it, and confirm it fails for the absence of the behavior about to be added. Write the minimum code that makes it pass, nothing else. State what you expect, then run. Where the run fails, fix the code. Where the requirement turns out to read differently, change the test and restart from the failing test. Where the structure needs a change, refactor, keeping behavior changes and structure changes separate and re-running the test after each change. Never write the test after the code it tests.

Where no test infrastructure exists, ask the user through AskUserQuestion whether to add it, and write no code until they answer. For a probe or spike, let an ephemeral test drive it, deleted when the probe ends.

### Design

Validate at system boundaries. Before a compatibility layer, ask first. Prefer fewer moving parts, fewer dependencies, fewer assumptions. Take the smallest working steps: correct first, clear second, fast third. Where an abstraction turns out wrong, redesign it. Where shared code branches per caller, split it into abstractions each caller owns. Ask how someone changes this next, then make that change easy. Name a thing for what it is. Where a function needs a comment to say what it does, rename it.

Never add complexity for a scenario that cannot happen. Never duplicate around a wrong abstraction. Never grow the interface with the implementation.
