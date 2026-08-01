# Readiness Claims

Named by [claims.md](../rules/claims.md). Read it from this path whenever a claim
that something serves as a foundation needs earning or denying with precision.

Calling something a foundation for a capability asserts that it bears the weight
the next layer puts on it. That assertion holds its form whether the foundation
takes the form of a span of code, a body of evidence, a material, an institution,
or an argument, and one discipline tests all of them.

## When this applies

Any of these words, applied to a thing you then build on: ready, in place,
already supports, anticipates, a substrate, a basis, a reserved hook, a slot, a
precondition met. Denying any of them applies too, at the same rigor.

The claim triggers this, so it fires inside work other rules already drive.
Auditing a system, exploring a codebase, planning a change, designing a solution,
and reasoning toward a decision each tend to produce a readiness conclusion near
the end. State that conclusion under this reference.

## The ladder

```sudolang
ReadinessClaims {
  Rung enum {
    // ordered low to high; a readiness decision turns on the gaps between rungs
    asserted          // claim made or intent recorded; nothing specified or realized
    specified         // mechanism, design, or argument laid out; fixed, not instantiated
    realizedUntested  // exists and holds in the conditions met so far, while the
                      // property it exists to provide has yet to meet the conditions
                      // that would stress it, and those differ from the conditions
                      // the dependent layer imposes
    provenUnderLoad   // defining property exercised and measured under the conditions
                      // the dependent layer will actually create
  }

  earn(claim: "X is a foundation for Y") {
    properties = enumerate the guarantees X must provide for Y to rest on it
    for p in properties {
      rung(p) = place on Rung, with evidence: measurement | trial | proof | citation
      noEvidence(p) => rung(p) <= specified
    }
    readiness(X, Y) = min(rung(p) for p in properties)
    // the weakest of the properties the next layer rests on governs the verdict;
    // one unexercised guarantee caps the whole claim, whatever the others reach
  }

  state(claim) {
    verdict: structurally present vs proven, plus the rung
    prerequisites: concrete, actionable steps to the next rung
    rank items by rung; each carries its own
    // several things labeled "anticipated" or "in place" usually sit on
    // different rungs; say which sits nearest bearing load and which
    // remains only asserted
  }

  deny(claim) {
    // two kinds of absence; saying which forms part of the claim
    immaturity       => same ladder, low rung; time or work advances it, so a delay
    differenceInKind => the thing lacks the defining property the capability needs
                        and provides another instead, so maturing it produces
                        nothing of what is missing and a separate foundation
                        must be built
  }
}
```

## Decision tests

Each test takes a question. Ask it before granting or denying the word.

**Which guarantees does the next layer actually rest on?** Enumerate those, and
place each one separately. A claim that names no properties has skipped the work.

**What evidence puts this property at that rung?** A measurement, a trial, a
proof, or a citation earns a rung. Absent one, the property sits at `specified`
however solid it looks.

**Which property sits lowest?** That one sets the verdict. Averaging across
properties hides exactly the gap a reader needs to see.

**Does the reader learn what would advance it?** A verdict without prerequisites
tells someone where they stand and leaves them no move.

**Immaturity or difference in kind?** Time fixes the first. Only a separate
foundation fixes the second, and conflating them sends someone to wait for
something that will never arrive.

## Calibration

Naming a foundation without naming its rung compresses four states into one word
and hides the distance a reader needs. Grant the rung explicitly, in the same
sentence that grants the word.

## Worked example

A claim that a body of evidence stands ready to support a recommendation.
Structurally it may look like a foundation: a plausible mechanism, supporting
observations, no contradicting result on hand. Yet the property the
recommendation actually rests on, that the effect holds under the conditions of
real use, may sit at only *realizedUntested*, shown in the small, in controlled
settings, and untried under the variation the recommendation will meet. That
evidence stands proven for the conditions reached, and open for the conditions
imposed. Verdict: structurally present, pre-inflection. Prerequisites to advance:
a trial under representative conditions, and a measure read under that load. The
bare claim "the evidence supports it" erases each of those distinctions, and with
them a reader's ability to decide whether to act yet.

Code follows the same ladder. A shared mechanism that could bear concurrent load
while having only ever run unstressed sits at *realizedUntested* for concurrency,
however solid it proves for the single-threaded case already met. Different
field, identical ladder.
