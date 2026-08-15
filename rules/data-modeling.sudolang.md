# Data Modeling

Build types that admit exactly the values you mean, so an illegal state never
reaches a runtime check. Five moves do most of that work, and each carries a
question that decides whether the move buys anything for the code at hand.

DataModeling {
  Applies { designing or changing types, data structures, schemas,
            interface signatures, or error channels }

  (about to write a runtime check, assertion, or panic for a state that
    "should never happen") =>
    a modeling decision hides there: apply FiveMoves, drawn from Alexis
    King's "The Unreasonable Effectiveness of Constructive Data Modeling"
    (SSW 2026), https://www.youtube.com/watch?v=0BXuYlNrUmE, then model the
    state out or accept the panic knowingly

  FiveMoves {
    ModelPositiveSpace {
      list the legal states and write one constructor per state, in place of
        taking a broader type and restricting it with advanced machinery: a
        first element paired with a rest, [T, ...T[]], serves a non-empty
        list, and EmailOnly | PhoneOnly | Both serves a user reachable by
        email, phone, or both, where two optional fields would admit a user
        reachable by neither
      test { can I list the legal states as cases?
             (yes) => construct them, and reach for restriction machinery
             only where I cannot }
    }

    ChooseARepresentationForTheCodeAtHand {
      representation decouples from interpretation
      no single representation holds privileged "correct" status: pick
        whichever serves the code reading it, a list of pairs for an
        even-length list, or a start time plus a non-negative duration for a
        time range ordered by construction where two raw timestamps would
        need a check, and convert at boundaries when neighbors prefer another
      test { am I defending one "true" representation?
             (yes) => ask which consumers each candidate serves, and let
             them decide }
    }

    LetTypesPropagateObligations {
      a type definition links producers and consumers that live far apart
        and have never read each other, so where someone adds a fourth
        contact case, the compiler's exhaustive matching reports every
        consumer site that must now handle it
      test { when a case gets added, does the compiler find every consumer?
             (it would miss one) => the model leaks interpretation into
             untyped convention }
    }

    BuyPrecisionWhereItDeletesAPanic {
      strengthen a type exactly where the alternative writes a "should never
        happen" throw, and keep the simplest representation everywhere else,
        leaving an email address a plain string until some code inspects its
        structure and a parsed EmailAddress earns its cost
      total functions form the goal, and type precision serves as one
        instrument: unused precision costs reuse and clarity while deleting
        nothing
      test { does this precision delete a panic, or only decorate? }
    }

    MoveObligationsToWhoeverCanDischargeThem {
      a required parameter pushes failure handling out to callers, who hold
        the context to respond sensibly. an optional value pulls it into code
        that may have no sane answer available.
      parse loose input into a precise type once, at a boundary, and pass the
        precise type inward, the move King's earlier essay names "parse,
        don't validate", since a check returning only a verdict discards what
        it computed and every site downstream checks it again
      test { which side of this boundary can actually handle the failure?
             place the obligation there }
    }
  }

  Calibration {
    Constraints {
      as simple as possible, but no simpler
      ask each move's test question before applying it, weigh the answer for
        the code at hand, skip the move on a "no", and hold none as an
        invariant
      product types, sum types, and exhaustive matching suffice for all
        five moves, with variadic tuples, GADTs, and refinement types
        offering conveniences on top
      newtype and unit wrappers (UserId vs PostId) slow mistakes down
        without making them unrepresentable, so adopt them by team
        judgment, priced as ergonomics
    }
    warn a model needing those conveniences to exist at all has probably
      drifted from positive space back into restriction
    (a precise type costs too much) => reach for an abstract type with a
      smart constructor, buying flexibility behind a guarded surface at the
      cost of impossibility at construction {
      validate inside the constructor and expose only methods that preserve
        the invariants, a guard holding only as well as its method set
        stays closed
    }
  }

  ForTests {
    Constraints {
      a state a type makes unrepresentable needs no test, the compiler
        having discharged that obligation
      (strengthening costs more than it pays) => write the test guarding
        the invariant: it stands in for the type you declined to build
    }
    warn a "should never happen" branch that a test must exercise signals a
      modeling smell {
      strengthen the type until the branch disappears
      | accept the panic knowingly and record why
    }
  }
}
