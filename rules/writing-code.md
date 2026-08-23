# Writing code

This applies when writing or modifying source code.

Find the boundaries and invariants first, and ask wherever acceptance criteria lack clarity. Write the isolated failing test, run it, and confirm it fails for the absence of the behavior you are about to add. Write the minimum code that makes it pass, and nothing else. Run the test. When it fails, fix the code. When you misread the requirement, change the test and start again from the first step. Refactor if needed, keeping behavior changes and structure changes separate, and re-run the test after each change.

When the project has no test infrastructure, flag the gap before writing code, and still write the test. For probe or spike work, write an ephemeral test to drive it and delete it when the probe ends, since ephemeral tests never merge.

Never add complexity for scenarios that cannot happen. Validate at system boundaries, and ask before adding a compatibility layer. Prefer fewer moving parts, fewer dependencies, fewer assumptions. Work in the smallest working steps: clear first, correct second, fast third. When an abstraction turns out wrong, redesign it instead of duplicating around it. When shared code branches per caller, split it into abstractions each caller owns. Ask how someone changes this next, and make that change easy. Name a thing for what it is, never for how it is made. When a function needs a comment to say what it does, rename it, and keep comments for why. Model data with types that admit only legal states, and buy precision exactly where it deletes a "should never happen" branch. Keep the interface from growing with the implementation.
