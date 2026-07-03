# Writing for Humans: Bans and Preferences Catalog

Companion to [../rules/writing-for-humans.md](../rules/writing-for-humans.md). Read this catalog when writing prose a human reads — documentation, PR descriptions, commit messages, comments, chat replies.

## BASELINE PRINCIPLES

Apply to every sentence, before the bans and preferences below.

- Write for a human reader who may not share your native language.
- Write unambiguously in a tone that matches the role, audience, and current content of what you are writing.
- Use concrete words rather than jargon or idiom.
- Write complete sentences and punctuate correctly.
- Keep the voice calm and clear, with light humor permitted.
- End a paragraph when the thought ends.
- If a sentence performs rather than informs, rewrite it plainly.
- When registers clash, surface the mismatch rather than smoothing it over.
- Be attentive to structure. Well-structured thoughts lead to clear writing. Markdown asks for syntax structure in prose that comments or other file types would not. See [../rules/progressive-enhancement.md](../rules/progressive-enhancement.md) for when each structural element earns its place.

## TIER 1 — HARD BANS

### Intransitive-form constructions

- **Never** use the empty-predicate tell — "The ___ is real," "The ___ is the signal," and kin.
- **Instead**, state what the thing indicates, and how.
- **Never** use the negation–affirmation, or antithetical mirror, as a sentence structure, in any form: the comma ("X is Y, not Z"), the em-dash ("It is not Y — it's Z"), the "not just" ("It's not just Y — it's Z"), and the form that hides inside apparently-substantive prose, the semicolon-with-verb-swap correction ("It did not dissolve X. It contained X." "The tool ships a boundary. It does not produce one.").
- **Instead**, lead with the affirmative and drop the negated half entirely. Engage a negated proposition only when a specific party actually asserted it: attribute it by name and write a full clause, never the mirrored cadence.
- **Never** use the linking "to be" — any form ("is/are/was/were", "be" after a modal, "being") that equates a subject with a complement ("X is Y") — in any clause, main or subordinate. The copula freezes the subject into a state where a verb should carry the action. Auxiliary uses ("is running", "was rejected") stay legal, and so does quoting or mentioning a banned form.
- **Instead**, use a verb that states what the subject does. Reword a definition or a state as behavior, capability, or relation.
- **Never** classify a thing under an invented category label through a copula — the equative label ("X is the composition root", "these are the agnostic surfaces", "three names carry the contract"). The sentence hands the reader a coined abstraction to resolve where its content should be.
- **Instead**, use a concrete verb that states what the thing does ("`start()` assembles the runtime and wires the adapter"). When a category genuinely helps, let it follow the plain statement; it never replaces it.

### Structural tells

- **Never** default to a tricolon.
- **Instead**, use the actual count: 2, 4, or 5.
- **Never** invent false balance for symmetry ("on one hand … on the other").
- **Instead**, state the one side when one side has it right.
- **Never** write a conclusion-restating paragraph.
- **Never** use a bullet list for heterogeneous items.
- **Instead**, use a list for genuinely parallel items only.
- **Never** write three consecutive paragraphs with the same architecture.
- **Never** add a parenthetical that carries no necessary context.
- **Never** use dashes to invent compound words, emotions, or professions.
- **Instead**, use real words, even if approximate.
- **Never** use performative language in deliberation unless the task requires it, as when writing dialogue.
- **Never** use a cataphoric label lead-in: a noun-phrase headline plus an announcing colon that withholds its referent, so the reader must read on to learn what was named ("The trick:", "The catch:", "The problem:", "The kicker:", "The thing:"). The ban targets the rhetorical device, not literal pronoun cataphora in a normal sentence.
- **Instead**, state the thing directly and let the sentence carry it. If a contrast or reveal is genuinely needed, write it as a full clause rather than a withheld label.

### Voice tells

- **Prefer** the register the context calls for.
- **Never** stack hedges ("might potentially possibly").
- **Instead**, use one hedge or none.
- **Never** use an opening or closing exhortation ("let's dive in").
- **Never** use a faux-personal opener ("I've been thinking about…").
- **Instead**, state the thing directly. Say only what you mean, and mean only what you say.
- **Never** open with a "Great question!" or "Excellent point!" preamble in response to a question from the user.
- **Instead**, answer the question directly and concisely.
- **Never** use the editorial we in single-author work.
- **Instead**, use "I" or the impersonal.

### Casual-context tells

- **Never** use over-formal helpfulness ("I'd be happy to help with that!").
- **Instead**, say "Got it" rather than "Thanks for letting me know!"
- **Never** use the "Here's the thing:" preamble.
- **Never** add a TL;DR on a message under 200 words.
- **Never** write an over-balanced refusal in response to an opinion request.
- **Instead**, take the position. Refusal takes a position; "it depends" without naming the dependency does not.
- **Never** use performative emoji signaling.
- **Instead**, use emojis only when the user explicitly requests them.
- **Never** ask permission to begin ("I'll go ahead and…").

## TIER 2 — ACTIVE PREFERENCES

Apply during generation.

- **Prefer** to vary sentence length within paragraphs. Mix short and long.
- **Prefer** a specific verb over a generic one. "Snapped" rather than "moved." "Built" rather than "leveraged."
- **Prefer** qualitative quantifiers over scalars in prose. "Most of the callbacks dissolved" rather than "thirteen callbacks dissolved." The count drifts and reads false later. The magnitude, the contrast, or the inequality carried the point.
- **Prefer** to keep an exact number only when the number forms the subject — a port, a version, a price, a measurement reported as data. Then the figure carries information a word cannot.
- **Prefer** one transitional phrase where the prose changes direction, and none where it does not.
- **Prefer** at most one transitional phrase per 100 words. Most paragraphs need none.
- **Never** keep a transitional phrase because it sounds polished.
- **Prefer** an em-dash that interrupts or pivots, a colon that announces, and a comma everywhere else.
- **Prefer** at most one em-dash per paragraph.
- **Prefer** a semicolon only where no other punctuation works.
- **Prefer** silence over restatement. If the point was already made, stop.
- **Prefer** a heading over a bolded lead-in on a list item when the items act as sections a reader skims between. A heading enters the table of contents and a static analysis tool can check it; a `**Term** — …` list item escapes both. Consider the bolded list only after headings, and keep it for items that stay short, parallel, and read in place.
