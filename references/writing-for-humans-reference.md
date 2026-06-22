# Writing for Humans: Bans and Preferences Catalog

Companion to [../rules/writing-for-humans.md](../rules/writing-for-humans.md). Read this catalog when writing prose a human reads — documentation, PR descriptions, commit messages, comments, chat replies.

## TIER 1 — HARD BANS

### Never-words

Replace each entry with its right-hand alternative. Only use the left word if its technical sense is exact.

| Never use | Use instead |
|-----------|-------------|
| delve into | look at, examine |
| intricate | complex, detailed |
| realm | field, area |
| pivotal | key, central |
| underscore | emphasize, show |
| tapestry | mix, range |
| commendable | solid |
| meticulous | careful, exact |
| robust | strong, reliable |
| seamless | smooth, easy |
| navigate (a topic) | work through, handle |
| foster | encourage, build |
| leverage | use |
| transformative | reshapes, changes |
| illuminate | show, clarify |
| harness | use |
| embark | start, begin |
| cultivate | build, grow |
| embrace | take up, accept |
| glean | find, learn |
| loop (for a sequence of steps) | process, workflow |

- **Never** use *crucial*, *vital*, *essential*, or *paramount* as a default intensifier.
- **Never** apply *dynamic* to anything that merely moves.
- **Never** apply *holistic* to anything more than one part.
- **Never** use a Kobak word to sound professional. Professionalism is precision, not diction.

### Intransitive-form constructions

- **Never** write "The ___ is real."
- **Never** write "The ___ is the signal."
- **Prefer** to state what the thing indicates, and how.
- **Never** use the negation–affirmation, or antithetical mirror, as a sentence structure, in any form: the comma ("X is Y, not Z"), the em-dash ("It is not Y — it's Z"), the "not just" ("It's not just Y — it's Z"), and the form that hides inside apparently-substantive prose, the semicolon-with-verb-swap correction ("It did not dissolve X. It contained X." "The tool ships a boundary. It does not produce one."). The mirror manufactures the feeling of a reversal — *you thought A, but really B* — without supplying one. The contrast is its own payload, and the parallel clauses plus the pivot punctuation read as insight the sentence has not earned.
- **Prefer** to lead with the affirmative and drop the negated half entirely. Engage a negated proposition only when a specific party actually asserted it: attribute it by name and write a full clause, never the mirrored cadence.

### Structural tells

- **Never** default to a tricolon.
- **Prefer** the actual count: 2, 4, or 5.
- **Never** invent false balance for symmetry ("on one hand … on the other").
- **Prefer** to state the one side when one side is right.
- **Never** write a conclusion-restating paragraph.
- **Never** use a bullet list for heterogeneous items.
- **Prefer** a list for genuinely parallel items only.
- **Never** write three consecutive paragraphs with the same architecture.
- **Never** add a parenthetical that carries no necessary context.
- **Never** use dashes to invent compound words, emotions, or professions.
- **Prefer** real words, even if approximate.
- **Never** use performative language in deliberation unless the task requires it, as when writing dialogue.
- **Never** use a cataphoric label lead-in: a noun-phrase headline plus an announcing colon that withholds its referent, so the reader must read on to learn what was named ("The trick:", "The catch:", "The problem:", "The kicker:", "The thing:"). This is the rhetorical device, not literal pronoun cataphora in a normal sentence.
- **Prefer** to state the thing directly and let the sentence carry it. If a contrast or reveal is genuinely needed, write it as a full clause rather than a withheld label.

### Voice tells

- **Never** use a corporate-neutral voice.
- **Prefer** the register the context calls for.
- **Never** stack hedges ("might potentially possibly").
- **Prefer** one hedge or none.
- **Never** use a closing exhortation ("let's dive in").
- **Never** use a faux-personal opener ("I've been thinking about…").
- **Prefer** to state the thing directly.
- **Never** open with a "Great question!" or "Excellent point!" preamble.
- **Prefer** to answer the question.
- **Never** use the editorial we in single-author work.
- **Prefer** "I" or the impersonal.

### Casual-context tells

- **Never** use over-formal helpfulness ("I'd be happy to help with that!").
- **Prefer** "Got it" over "Thanks for letting me know!"
- **Never** use the "Here's the thing:" preamble.
- **Never** add a TL;DR on a message under 200 words.
- **Never** write an over-balanced refusal in response to an opinion request.
- **Prefer** to take the position. Refusal is a position; "it depends" without naming the dependency is not.
- **Never** use performative emoji signaling.
- **Prefer** emojis only when the user explicitly requests them.
- **Never** ask permission to begin ("I'll go ahead and…").

## TIER 2 — ACTIVE PREFERENCES

Apply during generation.

- **Prefer** to vary sentence length within paragraphs. Mix short and long.
- **Prefer** a specific verb over a generic one. "Snapped" rather than "moved." "Built" rather than "leveraged."
- **Prefer** qualitative quantifiers over scalars in prose. "Most of the callbacks dissolved" rather than "thirteen callbacks dissolved." The count drifts and reads false later. The magnitude, the contrast, or the inequality was the point.
- **Prefer** to keep an exact number only when the number is the subject — a port, a version, a price, a measurement reported as data. Then the figure carries information a word cannot.
- **Prefer** one transitional phrase where the prose changes direction, and none where it does not.
- **Prefer** at most one transitional phrase per 100 words. Most paragraphs need none.
- **Never** keep a transitional phrase because it sounds polished.
- **Prefer** an em-dash that interrupts or pivots, a colon that announces, and a comma everywhere else.
- **Prefer** at most one em-dash per paragraph.
- **Prefer** a semicolon only where no other punctuation works.
- **Prefer** silence over restatement. If the point was already made, stop.
- **Prefer** a heading over a bolded lead-in on a list item when the items are sections a reader skims between. A heading enters the table of contents and is checkable by a static analysis tool; a `**Term** — …` list item is invisible to both. Consider the bolded list only after headings, and keep it for items that stay short, parallel, and read in place.
