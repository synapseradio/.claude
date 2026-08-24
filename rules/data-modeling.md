# Modeling data

This applies when designing or changing types, data structures, schemas, interface signatures, or error channels.

When about to write a runtime check, assertion, or panic for a state that "should never happen", treat that as a modeling decision. Apply five moves, drawn from Alexis King's "The Unreasonable Effectiveness of Constructive Data Modeling", then model the state out or accept the panic knowingly.

```sudolang
Moves {
  ModelPositiveSpace {
    do: list the legal states, write one constructor per state;
      restricting a broader type with advanced machinery comes second
    example: [T, ...T[]] serves a non-empty list. EmailOnly | PhoneOnly | Both serves
      a user reachable by email, phone, or both, where two optional fields would
      admit a user reachable by neither.
    test: can I list the legal states as cases? yes => construct them,
      restriction machinery only where I cannot
  }
  ChooseRepresentationForTheCodeAtHand {
    do: keep representation apart from interpretation, since none holds "correct"
      status; pick whichever serves the code reading it, converting at boundaries
      when neighbors prefer another
    example: a list of pairs for an even-length list, or a start time plus non-negative
      duration for a time range ordered by construction, where two raw timestamps
      would need a check
    test: am I defending one "true" representation? yes => ask which consumers
      each candidate serves, let them decide
  }
  LetTypesPropagateObligations {
    do: use the type definition to link producers and consumers that live far apart
      and have never read each other, so a fourth contact case makes exhaustive
      matching report every consumer site that must now handle it
    test: when a case gets added, does the compiler find every consumer?
      misses one => interpretation leaked into untyped convention, tighten the model
  }
  BuyPrecisionWhereItDeletesAPanic {
    do: strengthen a type exactly where the alternative writes a "should never happen"
      throw, keeping the simplest representation everywhere else: an email address
      stays a plain string until code inspects its structure and a parsed EmailAddress
      pays for itself. Aim at total functions, since unused precision costs reuse
      and clarity while deleting nothing.
    test: does this precision delete a panic, or not?
  }
  MoveObligationsToWhoeverCanDischargeThem {
    do: prefer a required parameter, which pushes failure handling out to callers
      holding the context to respond sensibly, over an optional value, which pulls it
      into code with no sane answer available. Parse loose input into a precise type
      once, at a boundary, and pass it inward, King's "parse, don't validate",
      since a check returning only a verdict discards what it computed
      and every downstream site checks again.
    test: which side of this boundary can handle the failure? place the obligation there
  }
}
```

## Calibrating the model

```sudolang
calibrate {
  make the model as simple as possible, and no simpler
  ask each move's test question before applying it, weigh it for the code at hand,
    skip the move on a "no", hold none as an invariant
  product types, sum types, and exhaustive matching first, since they suffice for
    all five moves; variadic tuples, GADTs, refinement types are conveniences on top
  newtype and unit wrappers (UserId vs PostId) by team judgment, priced as ergonomics,
    since they slow mistakes without making them unrepresentable
  the model needs those conveniences to exist at all =>
    check for drift from positive space back into restriction
  a precise type costs too much => an abstract type with a smart constructor,
    buying flexibility behind a guarded surface at the cost of impossibility
    at construction: validate inside it, expose only invariant-preserving methods,
    since the guard holds only while its method set stays closed
}
```

## Tests and types

```sudolang
testsAndTypes {
  no test covers a state a type makes unrepresentable, since the compiler discharged it
  strengthening costs more than it pays => write the test guarding the invariant
    in place of the type declined
  a test must exercise a "should never happen" branch => a modeling smell,
    strengthen the type until the branch disappears
}
```
