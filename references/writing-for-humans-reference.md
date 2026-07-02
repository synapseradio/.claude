# Writing for Humans: Bans and Preferences Catalog

Companion to [../rules/writing-for-humans.md](../rules/writing-for-humans.md). Read this catalog when writing prose a human reads — documentation, PR descriptions, commit messages, comments, chat replies.

## TIER 1 — HARD BANS

### Intransitive-form constructions

- **Never** use the empty-predicate tell — "The ___ is real," "The ___ is the signal," and kin.
- **Prefer** to state what the thing indicates, and how.
- **Never** use the negation–affirmation, or antithetical mirror, as a sentence structure, in any form: the comma ("X is Y, not Z"), the em-dash ("It is not Y — it's Z"), the "not just" ("It's not just Y — it's Z"), and the form that hides inside apparently-substantive prose, the semicolon-with-verb-swap correction ("It did not dissolve X. It contained X." "The tool ships a boundary. It does not produce one.").
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

- **Prefer** the register the context calls for.
- **Never** stack hedges ("might potentially possibly").
- **Prefer** one hedge or none.
- **Never** use an opening or closing exhortation ("let's dive in").
- **Never** use a faux-personal opener ("I've been thinking about…").
- **Prefer** to state the thing directly. Say only what you mean, and mean only what you say.
- **Never** open with a "Great question!" or "Excellent point!" preamble in response to a question from the user.
- **Prefer** to answer the question directly and concsisely.
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
