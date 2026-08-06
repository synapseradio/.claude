# Data Modeling

```sudolang
DataModeling {
  Applies { designing or changing types, data structures, schemas,
            interface signatures, or error channels }
  // construct types that admit exactly the values you mean, out of ordinary
  // parts: product types, sum types, exhaustive matching.
  // source: Alexis King, "The Unreasonable Effectiveness of Constructive
  // Data Modeling" (SSW 2026),
  // https://www.youtube.com/watch?v=0BXuYlNrUmE

  about to write a runtime check, assertion, or panic for a state that
    "should never happen" -> a modeling decision hides there {
    apply FiveMoves; model the state out, or accept the panic knowingly
  }

  FiveMoves {
    // each move carries one decision test. ask the test's question before
    // applying the move; a "no" means the move buys nothing here.

    ModelPositiveSpace {
      list legal states and write one constructor per state, in place of
        taking a broader type and restricting it with advanced machinery
      // a non-empty list: a first element paired with a rest, [T, ...T[]]
      // a user reachable by email, phone, or both: EmailOnly | PhoneOnly | Both,
      //   replacing two optional fields plus a comment pleading that at
      //   least one stays set
      test { can I list legal states as cases?
             yes -> construct them; restriction machinery only when I cannot }
    }

    ChooseARepresentationForTheCodeAtHand {
      representation decouples from interpretation
      // a list of pairs represents an even-length list; a start time plus a
      // non-negative duration represents an ordered time range, ordering
      // guaranteed by construction where two raw timestamps would need a check
      no single representation holds privileged "correct" status;
        pick whichever serves the code reading it, and convert at boundaries
        when neighbors prefer another
      test { am I defending one "true" representation?
             yes -> ask which consumers each candidate serves; let them decide }
    }

    LetTypesPropagateObligations {
      a type definition links producers and consumers that live far apart
        and have never read each other
      // a producer adds a fourth contact case -> exhaustive matching walks
      // every consumer to the site that must now handle it. this propagation,
      // rather than maximal precision, delivers most of a type system's
      // correctness value.
      test { when a case gets added, does the compiler find every consumer?
             it would miss one -> the model leaks interpretation into
             untyped convention }
    }

    BuyPrecisionWhereItDeletesAPanic {
      strengthen a type exactly where the alternative writes a "should never
        happen" throw; keep the simplest representation everywhere else
      // email addresses stay plain strings while no code inspects their
      // structure; a parsed EmailAddress earns its cost the day some code does
      total functions form the goal; type precision serves as one instrument,
        and unused precision costs reuse and clarity while deleting nothing
      test { does this precision delete a panic, or only decorate? }
    }

    MoveObligationsToWhoeverCanDischargeThem {
      a required parameter pushes failure handling out to callers, who hold
        the context to respond sensibly; an optional value pulls it into code
        that may have no sane answer available
      parse loose input into a precise type once, at a boundary, and pass the
        precise type inward
      // validation that merely checks and forgets leaves every downstream
      // reader re-proving what a parse would have recorded.
      // King's earlier essay names this: "parse, don't validate"
      test { which side of this boundary can actually handle the failure?
             place the obligation there }
    }
  }

  Calibration {
    as simple as possible, but no simpler
    every move answers to a trade-off: apply each as a question weighed
      per case; hold none as an invariant
    product types, sum types, and exhaustive matching suffice for all five moves
      // variadic tuples, GADTs, refinement types offer conveniences on top;
      // a model needing them to exist at all has probably drifted from
      // positive space back into restriction
    a precise type costs too much -> an abstract type with a smart constructor {
      validate inside the constructor; expose only methods preserving invariants
      // trades "unbreakable by construction" for flexibility plus a guarded
      // surface; the guard holds only as well as its method set stays closed
    }
    newtype and unit wrappers (UserId vs PostId) slow mistakes down without
      making them unrepresentable -> adopt by team judgment, priced as ergonomics
  }

  ForTests {
    a state a type makes unrepresentable needs no test
      // the compiler already discharged that obligation
    a "should never happen" branch a test must exercise -> a modeling smell {
      strengthen the type until the branch disappears
      | accept the panic knowingly and record why
    }
    strengthening costs more than it pays -> write the test guarding the
      invariant; it stands in for the type you declined to build
  }
}
```
