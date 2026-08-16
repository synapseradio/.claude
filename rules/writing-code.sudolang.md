WritingCode {
  Applies { writing or modifying source code }

  fn implement(behaviorChange) {
    find the boundaries and invariants first, and ask wherever acceptance
      criteria lack clarity
    |> write the isolated failing test, run it, and confirm it fails for the
       absence of the behavior you are about to add
    |> write the minimum code that makes it pass, and nothing else
    |> run the test, then match (the outcome) {
         case (it fails) => fix the code
         case (you misread the requirement) => change the test and start
           implement again at its first step
       }
    |> refactor if needed, keeping behavior changes and structure changes
       separate, and re-run the test after each change
  }

  constraint TestsAlways {
    (the project has no test infrastructure) => flag the gap before writing
      code, and still write the test
    (probe or spike work) => write an ephemeral test to drive it, and delete
      it when the probe ends, since ephemeral tests never merge
  }

  constraint Qualities {
    add no complexity for scenarios that cannot happen
    validate at system boundaries, and ask before adding a compatibility
      layer
    prefer fewer moving parts, fewer dependencies, fewer assumptions
    work in the smallest working steps: clear first, correct second, fast
      third
    (an abstraction turns out wrong) => redesign it rather than duplicate
      around it
    (shared code branches per caller) => split it into abstractions each
      caller owns
    ask how someone changes this next, and make that change easy
    name a thing for what it is, never for how it is made
    (a function needs a comment to say what it does) => rename it, and keep
      comments for why
    model data with types that admit only legal states, and buy precision
      exactly where it deletes a "should never happen" branch
    keep the interface from growing with the implementation
  }
}
