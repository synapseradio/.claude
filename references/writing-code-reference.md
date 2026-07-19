# Writing Code: Method and Qualities

## The implement flow

All work that changes behavior begins with an isolated test you expect to fail.

1. Seek boundaries and invariants to understand requirements first. If acceptance criteria lack clarity, ask before writing anything.
2. Write the failing test and run it. Confirm it fails for the right reason: the absence of the behavior you are about to add. A test that passes before you write the code proves nothing.
3. Implement the minimum code to make it pass. Nothing else.
4. Run the test. If it does not pass, fix the code. Change the test only when the requirement was misunderstood — then return to step 1.
5. Refactor if needed. Re-run after each change. Keep behavior changes and structure changes separate.

Never skip testing because no test infrastructure exists. Flag the gap before writing code.

The one exemption is probe or spike work — throwaway investigation to learn how something behaves. There the test may be ephemeral: write it to drive the probe, then delete it when the probe ends. Ephemeral tests never merge.

## Code qualities

Never add complexity for scenarios that cannot happen.

Validate at system boundaries. Ask before adding compatibility layers.

Prefer simplicity over cleverness. Fewer moving parts, fewer dependencies, fewer assumptions.

Work incrementally. Take the smallest working steps. Aim for clear first, correct second, fast third — never all at once.

Prefer duplication over wrong abstraction. Do not deduplicate unless the pieces represent the same concept and change for the same reasons. Inline shared code that branches per caller.

Design for change. Ask "how will someone change this next?" Make the next change easy.

Names describe the thing itself, not how it is made. Comments explain why, never what. If a function needs a comment to explain what it does, rename it.

Make invalid states impossible. Use types to enforce constraints.

Deep modules, simple interfaces. The interface should not grow with the implementation.

## Testing practice

### Run scope

Run only tests covering changed files. Map source to test by convention. The full suite runs only when the user asks, the scope warrants it, or no narrower mapping exists.

If the project has a "test changed files" tool, use it.

### Names

Use behavior-description names following the pattern `<subject> <verb> <behavior> [when <condition>]`. A failing test should read as a sentence.

### Assertions

Use the framework's assertion library. Never write ad-hoc checks that discard context on failure.

### Patterns

For scope tags, test isolation, mocks, and function shadowing, see [testing-patterns.md](./testing-patterns.md).
