# Writing code

This applies when writing or modifying source code.

```sudolang
fn writeCode {
  find the boundaries and invariants first, ask wherever acceptance criteria lack clarity
  loop {
    write the isolated failing test, run it, confirm it fails for the absence
      of the behavior about to be added
    write the minimum code that makes it pass, nothing else
    run: fails => fix the code
    misread the requirement => change the test, restart from the failing test
    refactor if needed, behavior changes and structure changes kept separate,
      re-running the test after each change
  }
  no test infrastructure => flag the gap before writing code, still write the test
  probe or spike => an ephemeral test drives it, deleted when the probe ends,
    since ephemeral tests never merge
}

Constraints {
  never add complexity for scenarios that cannot happen
  validate at system boundaries; a compatibility layer => ask first
  prefer fewer moving parts, fewer dependencies, fewer assumptions
  smallest working steps: clear first, correct second, fast third
  an abstraction turns out wrong => redesign it, never duplicate around it
  shared code branches per caller => split into abstractions each caller owns
  ask how someone changes this next, make that change easy
  name a thing for what it is, never for how it is made
  a function needs a comment to say what it does => rename it, keep comments for why
  model data with types that admit only legal states, buying precision exactly
    where it deletes a "should never happen" branch
  keep the interface from growing with the implementation
}
```
