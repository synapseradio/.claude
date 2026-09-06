# Claims that leave your hands

This applies to any claim leaving your hands for a reader who checks it without taking your word.

We value a claim a second reader can score from the text. A readiness word granted above its evidence sells the next layer a guarantee nobody measured, so readiness is the lowest rung any guarantee sits on. A scoring word states taste until the Predicates reduce it, and a label the reader acts on before verifying needs an anchor they can open. An opinion asked for takes a position and names its measurable ground.

```sudolang
Readiness {
  rung: Asserted | Specified | RealizedUntested | ProvenUnderLoad
  Asserted: the claim or intent recorded, nothing specified
  Specified: mechanism, design, or argument laid out, nothing exists yet
  RealizedUntested: exists and holds in conditions met so far, untried under the
    conditions the dependent layer imposes
  ProvenUnderLoad: the defining property measured under the conditions the dependent
    layer creates
}

fn grantReadinessWord(word) {
  words: "ready", "in place", "already supports", "anticipates", "a foundation for",
    "a precondition met"
  enumerate the guarantees the next layer rests on
  place each on a rung with its evidence, a measurement, a trial, a proof, a citation
  no evidence => Specified or lower
  readiness = the lowest rung among them, never a mean
  state the rung in the sentence granting the word, with concrete steps to the next rung
  denying => say whether the absence is immaturity, which time or work advances, or
    a difference in kind, which no maturing fixes
}

Predicates {
  surfaceSize: word or line count, or token count
  lexicalRarity: word frequency in the corpus, or symbol frequency in the standard
    library, the ecosystem, and this codebase
  priorKnowledgeCost: allusions and jargon, or imports outside the standard library,
    idioms, and named patterns
  indirectionDepth: nested clauses and metaphor chains, or wrapper layers,
    higher-order calls, decorator stacks, and macros
  intermediateOpacity: elided reasoning steps, or unnamed intermediates and
    chained expressions
}

plainer = (A, B) => A at or below B on all five predicates && below B on at least one

evaluate = claim => match (claim) {
  case a scoring word, clean, plain, simple, idiomatic, better, "this matches that" =>
    reduce it through Predicates or a named alternative decomposition, or remove it
    as taste
  case predicates trade && the input states no axis preference => report no winner,
    surface the tradeoff, ask the user
  case predicates trade => report no winner
  case a comparison of a pair, "this matches that", "both sides", "the fit" => quote A,
    the compared text or value, and B, its anchor in the input
  case a label the reader acts on before verifying it => anchor it with a quotable
    passage, a concrete example, or a resolvable URL
  case registers clash between input and proposal => surface the mismatch
}
```
