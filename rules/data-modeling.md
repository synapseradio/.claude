# Modeling data

This applies when designing or changing types, data structures, schemas, interface signatures, or error channels.

When about to write a runtime check, assertion, or panic for a state that "should never happen", treat that as a modeling decision. Apply five moves, drawn from Alexis King's "The Unreasonable Effectiveness of Constructive Data Modeling", then model the state out or accept the panic knowingly.

## Model positive space

List the legal states and write one constructor per state. Taking a broader type and restricting it with advanced machinery comes second. A first element paired with a rest, `[T, ...T[]]`, serves a non-empty list. `EmailOnly | PhoneOnly | Both` serves a user reachable by email, phone, or both, where two optional fields would admit a user reachable by neither. Test: can I list the legal states as cases? When yes, construct them, and reach for restriction machinery only where I cannot.

## Choose a representation for the code at hand

Keep representation apart from interpretation. No representation holds "correct" status. Pick whichever serves the code reading it, a list of pairs for an even-length list, or a start time plus a non-negative duration for a time range ordered by construction where two raw timestamps would need a check, and convert at boundaries when neighbors prefer another. Test: am I defending one "true" representation? When yes, ask which consumers each candidate serves, and let them decide.

## Let types propagate obligations

Use the type definition to link producers and consumers that live far apart and have never read each other, so that when someone adds a fourth contact case, exhaustive matching reports every consumer site that must now handle it. Test: when a case gets added, does the compiler find every consumer? When it would miss one, interpretation has leaked into untyped convention, so tighten the model.

## Buy precision where it deletes a panic

Strengthen a type exactly where the alternative writes a "should never happen" throw, and keep the simplest representation everywhere else, leaving an email address a plain string until some code inspects its structure and a parsed EmailAddress pays for itself. Aim at total functions, and use type precision as one instrument toward them, since unused precision costs reuse and clarity while deleting nothing. Test: does this precision delete a panic, or not?

## Move obligations to whoever can discharge them

Prefer a required parameter, which pushes failure handling out to callers who hold the context to respond sensibly, over an optional value, which pulls it into code that may have no sane answer available. Parse loose input into a precise type once, at a boundary, and pass the precise type inward, the move King's earlier essay names "parse, don't validate", since a check returning only a verdict discards what it computed and every site downstream checks it again. Test: which side of this boundary can handle the failure? Place the obligation there.

## Calibrating the model

Make the model as simple as possible, and no simpler. Ask each move's test question before applying it, weigh the answer for the code at hand, skip the move on a "no", and hold none as an invariant. Reach for product types, sum types, and exhaustive matching first, since they suffice for all five moves, and treat variadic tuples, GADTs, and refinement types as conveniences on top. Adopt newtype and unit wrappers (UserId vs PostId) by team judgment, priced as ergonomics, since they slow mistakes down without making them unrepresentable. When a model needs those conveniences to exist at all, check whether it has drifted from positive space back into restriction.

When a precise type costs too much, reach for an abstract type with a smart constructor, buying flexibility behind a guarded surface at the cost of impossibility at construction. Validate inside the constructor and expose only methods that preserve the invariants, since the guard holds only as long as its method set stays closed.

## Tests and types

No test covers a state a type makes unrepresentable, since the compiler discharged that obligation. When strengthening costs more than it pays, write the test guarding the invariant in place of the type you declined to build. When a test must exercise a "should never happen" branch, read that as a modeling smell, and strengthen the type until the branch disappears.
