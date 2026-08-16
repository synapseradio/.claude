DataModeling {
  Applies { designing or changing types, data structures, schemas,
            interface signatures, or error channels }

  (about to write a runtime check, assertion, or panic for a state that
    "should never happen") =>
    treat that as a modeling decision: apply FiveMoves, drawn from Alexis
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
      keep representation apart from interpretation
      grant no single representation "correct" status: pick whichever
        serves the code reading it, a list of pairs for an even-length list,
        or a start time plus a non-negative duration for a time range
        ordered by construction where two raw timestamps would need a check,
        and convert at boundaries when neighbors prefer another
      test { am I defending one "true" representation?
             (yes) => ask which consumers each candidate serves, and let
             them decide }
    }

    LetTypesPropagateObligations {
      use the type definition to link producers and consumers that live far
        apart and have never read each other, so where someone adds a fourth
        contact case, the compiler's exhaustive matching reports every
        consumer site that must now handle it
      test { when a case gets added, does the compiler find every consumer?
             (it would miss one) => the model leaks interpretation into
             untyped convention, so tighten it }
    }

    BuyPrecisionWhereItDeletesAPanic {
      strengthen a type exactly where the alternative writes a "should never
        happen" throw, and keep the simplest representation everywhere else,
        leaving an email address a plain string until some code inspects its
        structure and a parsed EmailAddress pays for itself
      aim at total functions, and use type precision as one instrument
        toward them: unused precision costs reuse and clarity while deleting
        nothing
      test { does this precision delete a panic, or only decorate? }
    }

    MoveObligationsToWhoeverCanDischargeThem {
      prefer a required parameter, which pushes failure handling out to
        callers who hold the context to respond sensibly, over an optional
        value, which pulls it into code that may have no sane answer
        available
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
      make the model as simple as possible, and no simpler
      ask each move's test question before applying it, weigh the answer for
        the code at hand, skip the move on a "no", and hold none as an
        invariant
      reach for product types, sum types, and exhaustive matching first,
        since they suffice for all five moves, and treat variadic tuples,
        GADTs, and refinement types as conveniences on top
      adopt newtype and unit wrappers (UserId vs PostId) by team judgment,
        priced as ergonomics, since they slow mistakes down without making
        them unrepresentable
    }
    warn (a model needs those conveniences to exist at all) => check whether
      it has drifted from positive space back into restriction
    (a precise type costs too much) => reach for an abstract type with a
      smart constructor, buying flexibility behind a guarded surface at the
      cost of impossibility at construction {
      validate inside the constructor and expose only methods that preserve
        the invariants, since the guard holds only as long as its method set
        stays closed
    }
  }

  ForTests {
    Constraints {
      write no test for a state a type makes unrepresentable, since the
        compiler discharged that obligation
      (strengthening costs more than it pays) => write the test guarding
        the invariant, in place of the type you declined to build
    }
    warn (a test must exercise a "should never happen" branch) => read that
      as a modeling smell {
      strengthen the type until the branch disappears
      | accept the panic knowingly and record why
    }
  }
}
