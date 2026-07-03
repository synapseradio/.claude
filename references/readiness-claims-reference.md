# Readiness Claims — Reference

Named by [readiness-claims.md](../rules/readiness-claims.md). Read it from this path when a claim that something serves as a foundation needs earning or denying with precision.

When you name something a foundation for a capability — a substrate, a basis, a precondition met, a thing described as "ready", "in place", or "already supports X" — you assert it bears the weight the next layer will put on it. The claim stays the same whether the foundation takes the form of a span of code, a body of evidence, a material, an institution, or an argument, and so does the discipline for testing it. The word carries the claim. This reference gives the vocabulary to calibrate it and the method to earn it.

## The maturity ladder

Anything offered as a foundation climbs through positions. Name the rung it occupies; do not blur them, because a readiness decision turns exactly on the gaps between rungs.

- **Asserted.** The claim is made or the intent is recorded. Nothing is yet specified or realized.
- **Specified.** The mechanism, design, or argument is laid out. Its shape is fixed; it has not been instantiated.
- **Realized, untested.** It exists and holds in the conditions met so far, but the property it exists to provide has not met the conditions that would stress it. It works where it has been reached, and those differ from the conditions the dependent layer imposes.
- **Proven under load.** The defining property has been exercised and measured under the conditions the dependent layer will actually create.

Naming a foundation without naming its rung compresses all four into one word and hides the distance the reader needs to see.

## What earns the word

Granting "foundation for Y" takes a check, not an assertion:

1. **Enumerate the properties.** What must the lower thing guarantee for Y to rest on it? List them.
2. **Place each on the ladder,** with its evidence — a measurement, a trial, a proof, a citation. A property with no evidence ranks at best as *specified*.
3. **Take the weakest.** A foundation's readiness equals its weakest load-bearing property, never the average. One unexercised guarantee caps the whole claim.

## Stating the claim

- Give an explicit verdict: structurally present versus proven, and the rung.
- List the prerequisites to reach the next rung — concrete and actionable, so the reader can move on them.
- Rank; do not flatten. When several things carry the label "anticipated" or "in place", they usually sit on different rungs. A uniform bucket misleads. Say which sits nearest load-bearing and which remains only asserted.

## Negative claims earn the word too

Denying the term takes the same rigor as granting it. Distinguish two kinds of absence. Absence can come from immaturity — the same ladder, a low rung, and time or work advances it. Or it can come from difference in kind — the thing lacks the defining property the capability needs and instead provides another, so no amount of maturing the present thing produces the missing one. The first names a delay; the second names a separate foundation that must be built. Saying which you mean forms part of the claim.

## Worked example

A claim that a body of evidence stands ready to support a recommendation. Structurally it may look like a foundation: a plausible mechanism, supporting observations, no contradicting result on hand. But the property the recommendation actually rests on — that the effect holds under the conditions of real use — may sit at only *realized, untested*: shown in the small, in controlled settings, never under the variation the recommendation will meet. The evidence is then proven for the conditions reached, not for the conditions imposed. Verdict: structurally present, pre-inflection. Prerequisites to advance: a trial under representative conditions, and a measure read under that load. The bare claim "the evidence supports it" erases each of those distinctions, and with them the reader's ability to decide whether to act yet.

The same shape governs code: a shared mechanism that could bear concurrent load but has only ever run unstressed sits at *realized, untested* for concurrency, however solid it proves for the single-threaded case already met. Different field, identical ladder.
