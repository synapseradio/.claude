# Writing Code

Behavior changes start from a failing test and stop at the minimum code that
passes it. What the implementation looks like afterward answers to the
qualities collected below.

WritingCode {
  Applies { writing or modifying source code }

  ImplementFlow {
    Applies { adding or modifying behavior }
    tests answer to ./testing.sudolang.md for their quality
      when that path-scoped file has not loaded, read it

    fn implement(behaviorChange) {
      seek boundaries and invariants to understand the requirements first, and
        ask before writing anything wherever acceptance criteria lack clarity
      |> write the isolated failing test and run it, confirming that it fails
         for the right reason: the absence of the behavior you are about to add
      |> implement the minimum code to make it pass, and nothing else
      |> run the test, then match (the outcome) {
           case (it fails) => fix the code
           case (the requirement was misunderstood) =>
             change the test, then start implement again at its first step
         }
      |> refactor if needed, keeping behavior changes and structure changes
         separate, and re-running the test after each change
    }

    require testing happens even where the project has no test
      infrastructure: flag the gap before writing code, and never skip the test

    Exemption {
      probe or spike work, a throwaway investigation to learn how something
        behaves, may take an ephemeral test: write it to drive the probe, and
        delete it when the probe ends
      ephemeral tests never merge
    }
  }

  CodeQualities {
    never add complexity for scenarios that cannot happen
    validate at system boundaries, and ask before adding compatibility layers
    prefer simplicity over cleverness: fewer moving parts, fewer dependencies,
      fewer assumptions
    work incrementally, in the smallest working steps: clear first, correct
      second, fast third, never all at once
    never duplicate {
      when an abstraction turns out wrong, redesign it rather than duplicate
        around it
      when shared code branches per caller, split it into abstractions each
        caller can own
    }
    design for change: ask how someone will change this next, and make that
      next change easy
    names describe the thing itself, never how it is made
    comments explain why, never what: rename any function that needs a comment
      to say what it does
    model data constructively, with types that admit only legal states, and buy
      precision exactly where it deletes a "should never happen" branch
      via(DataModeling)
    deep modules, simple interfaces: keep the interface from growing with the
      implementation
  }
}
