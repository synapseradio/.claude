# Modeling data

This applies when designing or changing types, data structures, schemas, interface signatures, or error channels.

We value a type that admits only legal states, bought exactly where it deletes a "should never happen" branch. A runtime check for such a state is a modeling decision, and the five moves come from Alexis King's talk on constructive data modeling at https://www.youtube.com/watch?v=0BXuYlNrUmE. Product types, sum types, and exhaustive matching suffice for all five, so a model reaching for variadic tuples, GADTs, or refinement types has drifted back into restriction, and a newtype wrapper slows a mistake without making it unrepresentable, so it gets priced as ergonomics. The compiler discharges a state a type makes unrepresentable, so no test covers it, and unused precision costs reuse and clarity while deleting nothing.

```sudolang
panic = check => match (check) {
  case a runtime check, assertion, or throw for a state that should never happen =>
    ask each Move's test, apply the move on a yes, skip it on a no, then model the
    state out or accept the panic knowingly
  case a test must exercise a "should never happen" branch => strengthen the type until
    the branch disappears
  case strengthening costs more than it pays => the test guarding the invariant, in
    place of the type declined
  case a precise type costs too much => an abstract type with a smart constructor,
    validated inside, exposing only invariant-preserving methods, its method set
    kept closed
}

Moves {
  ModelPositiveSpace {
    do: list the legal states, write one constructor per state
    example: EmailOnly | PhoneOnly | Both for a user reachable by email, phone, or both,
      where two optional fields admit a user reachable by neither
    test: can I list the legal states as cases?
  }
  ChooseRepresentationForTheCodeAtHand {
    do: pick whichever representation serves the code reading it, converting at boundaries
    example: a start time plus a non-negative duration for a time range ordered by
      construction, where two raw timestamps need a check
    test: am I defending one true representation?
  }
  LetTypesPropagateObligations {
    do: link producers and consumers through the type definition, so a new case makes
      exhaustive matching report every consumer site
    example: a fourth contact kind added to the union fails every match that lacks it
    test: when a case gets added, does the compiler find every consumer?
  }
  BuyPrecisionWhereItDeletesAPanic {
    do: strengthen the type at the site of a "should never happen" throw, keep the
      simplest representation at every other site
    example: an email address stays a plain string until code inspects its structure
    test: does this precision delete a panic?
  }
  MoveObligationsToWhoeverCanDischargeThem {
    do: a required parameter over an optional value, and loose input parsed into a
      precise type once at a boundary and passed inward
    example: a non-empty list parsed at the API edge, where a check returning only a
      verdict makes every downstream site check again
    test: which side of this boundary can handle the failure?
  }
}
```
