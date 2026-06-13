# Evaluative Language: Decomposing Judgment Words

Judgment words ("clean," "plain," "idiomatic") are claims. Rule: any such word in output handed to another reader must reduce to predicates they can score from the inputs — or be removed.

## The Second-Reader Test

An instruction, evaluation, or claim is verifiable iff a second reader — human or agent, with access only to the inputs and the candidates — can check every clause. No access to the first agent's internal state may be required.

This is distinct from reasoning-principles.md Principle 2 (seek disconfirmation), which governs your own conclusions. The second-reader test governs the output you hand to another reader.

## A/B Anchoring

When a claim references a pair — "this matches that," "both sides," "the coincidence," "the fit" — name Side A and Side B with textual anchors:

- A: the quoted text, cited artifact content, or stated value being compared.
- B: the textual anchor in the input (task description, user's stated purpose, circumstance described in text).

Do not use "both sides," "the pair," or "the fit" without naming A and B. An unnamed pair is a claim about the agent's disposition and fails the second-reader test.

Special case: citing an artifact. When your output cites a quote, link, or reference, you are implicitly claiming A (the artifact's semantic content) fits B (the stated context of use). Name both; make the fit checkable.

Special case: naming versus backing. Test: *does the reader have to verify the claim before acting?*

- No → a label names the referent. "We follow REST." "This is idiomatic Python." Sufficient.
- Yes → anchor the claim. "Per PEP 8 §3, `u` is acceptable" needs a quotable passage, a concrete example of the pattern, or a resolvable URL.

`[?]` marks uncertainty; it does not substitute for a missing anchor on a load-bearing claim.

## The Five-Predicate Harness

For "plainer" — and, by extension, "cleaner," "simpler," "more idiomatic" — reduce to:

| Predicate             | Prose instantiation                              | Code instantiation                                                    |
|-----------------------|--------------------------------------------------|-----------------------------------------------------------------------|
| Surface size          | token / word count                               | token / line count                                                    |
| Lexical rarity        | word frequency in the working corpus             | symbol frequency in stdlib, ecosystem, this codebase                  |
| Prior-knowledge cost  | allusions, jargon, named references              | non-stdlib imports, language idioms, named patterns                   |
| Indirection depth     | nested clauses, metaphor or pronoun chains       | wrapper layers, higher-order calls, decorator stacks, macro expansion |
| Intermediate opacity  | elided reasoning steps                           | unnamed intermediate values, chained expressions                      |

### Reduction rule

`plainer(a, b)` holds iff `a ≤ b` on all five predicates and strictly `<` on at least one. When predicates trade — `a` wins on size, `b` wins on indirection — the harness returns **no winner**, not a guess.

### When the harness returns no winner

Do not pick by taste. Either:

- Follow an explicit axis preference from the input ("prefer the shorter," "prefer the more common").
- Surface the tradeoff and ask the user (CLAUDE.md Core Rule 4).

## Register Check

When the input and the proposal occupy incompatible registers, surface the mismatch rather than smooth it over. Register is detectable as per-clause lexical and syntactic shifts in the provided text. The check operates on pairs of texts (input ↔ proposal), not on the agent's disposition.

## Usage Contract

Evaluative words in outputs handed to another reader must either:

- Reduce through this harness, or through an explicitly named alternative decomposition, or
- Be removed.

Words that resist decomposition are taste. Taste in an instruction is a failure of respect.

Exemption: internal drafts, exploratory thinking, and reasoning the agent holds for itself are not subject to this contract. The contract applies at the boundary — when the output is handed to another reader.
