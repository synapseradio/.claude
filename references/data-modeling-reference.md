# Constructive Data Modeling

Construct types that admit exactly the values you mean, out of ordinary parts: product types, sum types, exhaustive matching. Source: Alexis King, ["The Unreasonable Effectiveness of Constructive Data Modeling"](https://www.youtube.com/watch?v=0BXuYlNrUmE) (SSW 2026).

## When this applies

Read this when designing or changing types, data structures, schemas, interface signatures, or error channels. Read it again when about to write a runtime check, assertion, or panic for a state that "should never happen": that check marks a spot where a modeling decision hides.

## Five moves

Each move carries one decision test. Ask the test's question before applying the move; a "no" means the move buys nothing here.

### Model positive space

List legal states and write one constructor per state, in place of taking a broader type and restricting it with advanced type-system machinery. A non-empty list becomes a first element paired with a rest list (`[T, ...T[]]`). A user reachable by email, phone, or both becomes a three-case union `EmailOnly | PhoneOnly | Both`, replacing two optional fields plus a comment pleading that at least one stays set.

Test: can I list legal states as cases? If yes, construct them; reach for restriction machinery only when I cannot.

### Choose a representation for the code at hand

Representation decouples from interpretation. A list of pairs represents an even-length list. A start time plus a non-negative duration represents an ordered time range, with ordering guaranteed by construction where two raw timestamps would need a check. No single representation holds privileged "correct" status; pick whichever one serves the code reading it, and convert at boundaries when neighbors prefer another.

Test: am I defending one "true" representation? If yes, ask which consumers each candidate serves, and let them decide.

### Let types propagate obligations

A type definition links producers and consumers that live far apart and have never read each other. When a producer adds a fourth contact case, exhaustive matching walks every consumer to the site that must now handle it. This propagation, rather than maximal precision, delivers most of a type system's correctness value.

Test: when a case gets added, does the compiler find every consumer? If it would miss one, the model leaks interpretation into untyped convention.

### Buy precision where it deletes a panic

Strengthen a type exactly where the alternative writes a "should never happen" throw, and keep the simplest representation everywhere else. Email addresses can stay plain strings for as long as no code inspects their structure; a parsed `EmailAddress` type earns its cost the day some code does. Total functions form the goal. Type precision serves as one instrument toward it, and unused precision costs reuse and clarity while deleting nothing.

Test: does this precision delete a panic, or only decorate?

### Move obligations to whoever can discharge them

Making a parameter required pushes failure handling out to callers, who hold the context to respond sensibly. Accepting an optional value pulls failure handling into code that may have no sane answer available. Parse loose input into a precise type once, at a boundary, and pass the precise type inward; validation that merely checks and forgets leaves every downstream reader re-proving what a parse would have recorded. (King's earlier essay names this parse, don't validate.)

Test: which side of this boundary can actually handle the failure? Place the obligation there.

## Calibration

Make each model as simple as possible, but no simpler. Every move above answers to a trade-off, so apply each one as a question to weigh per case, and hold none of them as an invariant.

Product types, sum types, and exhaustive matching suffice for all five moves. Variadic tuples, GADTs, refinement types, and similar machinery offer conveniences on top; a model needing them to exist at all has probably drifted from positive space back into restriction.

When constructing a precise type costs too much, an abstract type with a smart constructor serves as a legitimate fallback: validate inside a constructor, expose only methods that preserve invariants. This trades "invariant unbreakable by construction" for flexibility plus a guarded surface, and the guard holds only as well as its method set stays closed.

Newtype and unit wrappers (`UserId` versus `PostId`) slow mistakes down without making them unrepresentable. Adopt them by team judgment, priced as ergonomics.

## What this means for tests

A state a type makes unrepresentable needs no test; a compiler already discharged that obligation. A "should never happen" branch that a test must exercise signals a modeling smell: either strengthen the type until the branch disappears, or accept the panic knowingly and record why. When strengthening costs more than it pays, write the test that guards the invariant, and let it stand in for the type you declined to build.
