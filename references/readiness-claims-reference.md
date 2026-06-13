# Readiness Claims — Reference

Named by [readiness-claims.md](../rules/readiness-claims.md). Read it from this path when a claim that something is a foundation needs to be earned or denied with precision.

When you name something a foundation for a capability — a substrate, a basis, a precondition met, a thing that is "ready", "in place", or "already supports X" — you assert it bears the weight the next layer will put on it. The claim is the same whether the foundation is a span of code, a body of evidence, a material, an institution, or an argument, and so is the discipline for testing it. The word is the claim. This reference gives the vocabulary to calibrate it and the method to earn it.

## The maturity ladder

Anything offered as a foundation climbs through positions. Name the rung it occupies; do not blur them, because the gaps between rungs are exactly what a readiness decision turns on.

- **Asserted.** The claim is made or the intent is recorded. Nothing is yet specified or realized.
- **Specified.** The mechanism, design, or argument is laid out. Its shape is fixed; it has not been instantiated.
- **Realized, untested.** It exists and holds in the conditions met so far, but the property it exists to provide has not met the conditions that would stress it. It works where it has been reached, and those are not the conditions the dependent layer imposes.
- **Proven under load.** The defining property has been exercised and measured under the conditions the dependent layer will actually create.

Naming a foundation without naming its rung compresses all four into one word and hides the distance the reader needs to see.

## What earns the word

Granting "foundation for Y" is a check, not an assertion:

1. **Enumerate the properties.** What must the lower thing guarantee for Y to rest on it? List them.
2. **Place each on the ladder,** with its evidence — a measurement, a trial, a proof, a citation. A property with no evidence is at best *specified*.
3. **Take the weakest.** A foundation's readiness is its weakest load-bearing property, never the average. One unexercised guarantee caps the whole claim.

## Stating the claim

- Give an explicit verdict: structurally present versus proven, and the rung.
- List the prerequisites to reach the next rung — concrete and actionable, so the reader can move on them.
- Rank; do not flatten. When several things are "anticipated" or "in place", they usually sit on different rungs. A uniform bucket misleads. Say which is nearest load-bearing and which is only asserted.

## Negative claims earn the word too

Denying the term takes the same rigor as granting it. Distinguish two kinds of absence. A thing can be absent because it is immature — the same ladder, a low rung, and time or work advances it. Or it can be absent because it is different in kind — it lacks the defining property the capability needs and instead provides another, so no amount of maturing the present thing produces the missing one. The first is a delay; the second is a separate foundation that must be built. Saying which you mean is part of the claim.

## Worked example

A claim that a body of evidence is ready to support a recommendation. Structurally it may look like a foundation: a plausible mechanism, supporting observations, no contradicting result on hand. But the property the recommendation actually rests on — that the effect holds under the conditions of real use — may be only *realized, untested*: shown in the small, in controlled settings, never under the variation the recommendation will meet. The evidence is then proven for the conditions reached, not for the conditions imposed. Verdict: structurally present, pre-inflection. Prerequisites to advance: a trial under representative conditions, and a measure read under that load. The bare claim "the evidence supports it" erases each of those distinctions, and with them the reader's ability to decide whether to act yet.

The same shape governs code: a shared mechanism that could bear concurrent load but has only ever run unstressed is *realized, untested* for concurrency, however solid it is for the single-threaded case already met. Different field, identical ladder.
