# Writing code

This applies when writing or modifying source code.

We value code whose behavior a test asserted before the code existed, and whose next change is easy. A test written after the code passes for reasons nobody checked, so each loop opens on a failing test and each run on a stated expectation. An ephemeral test never merges, so a probe's test dies with the probe. Complexity for a scenario that cannot happen and an interface grown with its implementation each cost the next reader.

```sudolang
fn writeCode() {
  find the boundaries and invariants first, ask wherever acceptance criteria lack clarity
  predict the failures before modifying code
  loop {
    write the isolated failing test, run it, confirm it fails for the absence of the
      behavior about to be added
    write the minimum code that makes it pass, nothing else
    state what you expect, then run
    the run fails => fix the code
    misread the requirement => change the test, restart from the failing test
    the structure needs a change => refactor, behavior changes and structure changes
      kept separate, re-running the test after each change
  }
  no test infrastructure => flag the gap before writing code, still write the test
  a probe or spike => an ephemeral test drives it, deleted when the probe ends
}

Design {
  validate at system boundaries
  a compatibility layer => ask first
  fewer moving parts, fewer dependencies, fewer assumptions
  smallest working steps: correct first, clear second, fast third
  an abstraction turns out wrong => redesign it
  shared code branches per caller => split into abstractions each caller owns
  ask how someone changes this next, make that change easy
  name a thing for what it is
  a function needs a comment to say what it does => rename it, keep comments for why
  model data with types that admit only legal states, buying precision exactly where
    it deletes a "should never happen" branch
}

require never add complexity for a scenario that cannot happen
require never duplicate around a wrong abstraction
require keep the interface from growing with the implementation
```
