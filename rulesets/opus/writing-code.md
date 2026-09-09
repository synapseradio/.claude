<rule name="writing-code">

  <applies_when>
    You are writing or modifying source code.
  </applies_when>

  <optimize_for>
    code whose behavior a test asserted before the code existed, and whose next change is easy.
    <why_it_matters>
      A test that fails before the code exists shows the behavior absent, and the pass that follows reports it arriving. A test written after the code passes for reasons that have not been discussed, and may not be valid constraints. A probe's test asserts what the probe asked, and it ends with the probe. Complexity for a scenario that cannot happen and an interface grown with its implementation each spend valuable attention on what no requirement asked for.
    </why_it_matters>
  </optimize_for>

  <do name="write code">
    Find the boundaries and invariants first, and ask wherever acceptance criteria lack clarity. Predict the failures before modifying code. Then repeat this loop. Write the isolated failing test, run it, and confirm it fails for the absence of the behavior about to be added. Write the minimum code that makes it pass, nothing else. State what you expect, then run. Where the run fails, fix the code. Where the requirement turns out to read differently, change the test and restart from the failing test. Where the structure needs a change, refactor, keeping behavior changes and structure changes separate and re-running the test after each change.

    Where no test infrastructure exists, flag the gap before writing code, and still write the test. For a probe or spike, an ephemeral test drives it, deleted when the probe ends.
  </do>

  <do name="design">
    Validate at system boundaries. Before a compatibility layer, ask first. Prefer fewer moving parts, fewer dependencies, fewer assumptions. Take the smallest working steps: correct first, clear second, fast third. Where an abstraction turns out wrong, redesign it. Where shared code branches per caller, split it into abstractions each caller owns. Ask how someone changes this next, and make that change easy. Name a thing for what it is. Where a function needs a comment to say what it does, rename it, and keep comments for why. Model data with types that admit only legal states, buying precision exactly where it deletes a "should never happen" branch.
  </do>

  <require>
    Never add complexity for a scenario that cannot happen. Never duplicate around a wrong abstraction. Never grow the interface with the implementation.
  </require>

</rule>
