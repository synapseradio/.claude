# Readiness Claims — Reference

Named by [readiness-claims.md](../rules/readiness-claims.md). Read it from this path when a claim that something serves as a foundation needs earning or denying with precision.

When you name something a foundation for a capability — a substrate, a basis, a precondition met, a thing described as "ready", "in place", or "already supports X" — you assert it bears the weight the next layer will put on it. The claim stays the same whether the foundation takes the form of a span of code, a body of evidence, a material, an institution, or an argument, and so does the discipline for testing it.

```sudolang
ReadinessClaims {
  Rung enum {
    // ordered low to high; a readiness decision turns exactly on the gaps between rungs
    asserted          // claim made or intent recorded; nothing specified or realized
    specified         // mechanism, design, or argument laid out; shape fixed, not instantiated
    realizedUntested  // exists and holds in the conditions met so far, but the property it
                      // exists to provide has not met the conditions that would stress it —
                      // and those differ from the conditions the dependent layer imposes
    provenUnderLoad   // defining property exercised and measured under the conditions the
                      // dependent layer will actually create
  }

  earn(claim: "X is a foundation for Y") {
    properties = enumerate the guarantees X must provide for Y to rest on it
    for p in properties {
      rung(p) = place on Rung, with evidence: measurement | trial | proof | citation
      noEvidence(p) => rung(p) <= specified
    }
    readiness(X, Y) = min(rung(p) for p in properties)
    // the weakest load-bearing property, never the average;
    // one unexercised guarantee caps the whole claim
  }

  state(claim) {
    verdict: structurally present vs proven, plus the rung
    prerequisites: concrete, actionable steps to the next rung
    rank items; never flatten to one bucket
    // several things labeled "anticipated" or "in place" usually sit on
    // different rungs — say which sits nearest load-bearing and which
    // remains only asserted
  }

  Constraints {
    Naming a foundation without naming its rung compresses all four rungs
      into one word and hides the distance the reader needs to see.
    Denying the word takes the same rigor as granting it — see deny().
  }

  deny(claim) {
    // distinguish two kinds of absence; saying which forms part of the claim
    immaturity       => same ladder, low rung; time or work advances it — a delay
    differenceInKind => the thing lacks the defining property the capability
                        needs and provides another instead; no amount of
                        maturing it produces the missing one — a separate
                        foundation must be built
  }
}
```

## Worked example

A claim that a body of evidence stands ready to support a recommendation. Structurally it may look like a foundation: a plausible mechanism, supporting observations, no contradicting result on hand. But the property the recommendation actually rests on — that the effect holds under the conditions of real use — may sit at only *realizedUntested*: shown in the small, in controlled settings, never under the variation the recommendation will meet. The evidence is then proven for the conditions reached, not for the conditions imposed. Verdict: structurally present, pre-inflection. Prerequisites to advance: a trial under representative conditions, and a measure read under that load. The bare claim "the evidence supports it" erases each of those distinctions, and with them the reader's ability to decide whether to act yet.

The same shape governs code: a shared mechanism that could bear concurrent load but has only ever run unstressed sits at *realizedUntested* for concurrency, however solid it proves for the single-threaded case already met. Different field, identical ladder.
