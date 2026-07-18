# Writing for Humans: Directives and Preferences

Companion to [../rules/writing-for-humans.md](../rules/writing-for-humans.md). Read this when writing prose a human receives — documentation, PR descriptions, commit messages, comments, chat replies.

Each section names a construction, quotes it in the forms it takes, and gives the directive that replaces it. The quoted examples show the shape to recognize. The prose around them says what to write instead.

## Baseline

These hold for every sentence, ahead of everything below.

Write for someone who may not share your native language, in a tone matching the role, the audience, and the content at hand. Choose concrete words over jargon and idiom. Punctuate correctly and finish your sentences. Keep the voice calm and clear, and allow light humor. End a paragraph when the thought ends.

A sentence that performs rather than informs wants rewriting in plain form. When registers clash, surface the mismatch rather than smoothing it over.

Structure deserves attention, since well ordered thoughts produce clear writing. Markdown invites syntax that a source comment or a commit message would refuse. [../rules/progressive-enhancement.md](../rules/progressive-enhancement.md) covers when each structural element earns its place.

## Tier 1: holds absolutely

### Predicates that assert existence

"The burnout is real." "The threat is real." "The opportunity is the signal." Mentioning a thing already presupposes that it exists, so a predicate asserting its existence performs emphasis where it should supply it. State what the thing indicates and how the indication works.

### Negation–affirmation mirrors

Also called antithetical mirrors, these wear several disguises. The comma form runs "X is Y, not Z." The em-dash form runs "It is not Y — it's Z." The "not just" form runs "It's not just Y — it's Z." The subtlest version hides inside apparently substantive prose as a verb swap across two sentences: "It did not dissolve X. It contained X." Or: "The tool ships a boundary. It does not produce one."

Lead with the affirmative and let the negated half go unwritten. Engage a negated proposition only where some specific party actually asserted it, and then attribute it by name and give it a full clause of its own.

### Linking "to be"

Any form that equates a subject with a complement — "is", "are", "was", "were", "be" after a modal, "being" — freezes the subject into a state where a verb should carry the action. This covers main and subordinate clauses alike. Use a verb that states what the subject does, and reword a definition or a state as behavior, capability, or relation.

Auxiliary uses stay legal, as in "is running" or "was rejected". So does quoting or mentioning the construction itself.

### Categories applied through a copula

"X is the composition root." "These are the agnostic surfaces." "Three names carry the contract." Each files something under a coined category through a copula, handing the audience an abstraction to resolve where the content belongs. Let a concrete verb say what the thing does: "`start()` assembles the runtime and wires the adapter." Where a category genuinely helps, let it follow the plain statement rather than stand in for it.

### Padding and invented symmetry

Groups drift toward three items because three sounds finished. List exactly the items there are, whatever their number. This governs how many items you present. Whether to name the count in the sentence falls under the quantifier preference below, where a bare total still drops.

False balance for symmetry, "on one hand … on the other", earns nothing when one side has it right. Say which side.

A closing paragraph that restates the conclusion goes, and so does a parenthetical carrying no necessary context. Three consecutive paragraphs built the same way want reshaping. Lists belong to genuinely parallel items, and heterogeneous items belong in prose.

Dashes never invent compound words, emotions, or professions. Real words serve, even approximate ones.

Performative language waits for tasks that call for it, such as writing dialogue. Deliberation asks for the plain register.

### Labels that withhold their referent

"The trick:" "The catch:" "The problem:" "The kicker:" "The thing:" A noun phrase headline plus an announcing colon withholds its referent, so the audience must read on to learn what got named. State the thing directly and let the sentence carry it. Where a contrast or a reveal genuinely earns its place, write it as a full clause. Literal pronoun cataphora inside an ordinary sentence falls outside this.

### Voice

Write in the register the context calls for. Stacked hedges, "might potentially possibly", collapse to one hedge or none.

Open and close on the substance. Exhortations like "let's dive in" go, and so do faux personal openers like "I've been thinking about…". Say only what you mean, and mean only what you say. Answer a question directly, without a "Great question!" or "Excellent point!" preamble.

Single-author work takes "I" or the impersonal. The editorial we waits for work that genuinely has several authors.

### Personification

"The gauge stays honest." "The rule guards it." "The code wants." "The data believes." A noun naming something without agency acquires none by grammar. Name whoever acts, or state the property directly: "the gauge tracks clarity only while gains trace back to clarity gains."

Personification has an inverse worth catching in the same pass. "The system decided" and "mistakes were made" strip a chooser out of a sentence where somebody chose. [../rules/presupposition.md](../rules/presupposition.md) covers both directions, along with definite articles on terms you coined and mental verbs applied to tools.

### Virtue verdicts on your own work

"Honestly." "To be honest." "An honest reading." "A rigorous analysis." "A careful review." Awarding any of these to your own claims, constructs, or work costs nothing and so carries no evidence. The verdict reveals only that the writer expected doubt, and the audience's prior shifts toward the opposite. Same engine as the empty predicate: asserting what a trustworthy statement would leave presupposed invites the question of why it needed asserting. Show the mechanism or the evidence that would earn the virtue, and leave the word itself for the audience to award.

### Casual register

Say "Got it." Over formal helpfulness goes, "I'd be happy to help with that!" and "Thanks for letting me know!" alike. So does the "Here's the thing:" preamble, and so does asking permission with "I'll go ahead and…". Just begin.

A message under 200 words carries no TL;DR. When asked for an opinion, take the position. Refusal counts as one, though "it depends" without naming the dependency does not. Emojis wait for an explicit request.

## Tier 2: applied while drafting

Vary sentence length within paragraphs, mixing short against long. Reach for the specific verb over the generic one: "snapped" rather than "moved", "built" rather than "leveraged".

Qualitative quantifiers beat scalars in prose. "Most of the callbacks dissolved" outlasts "thirteen callbacks dissolved", because the count drifts and reads false later, while the magnitude or the contrast carried the point. Keep an exact number where the number forms the subject — a port, a version, a price, a measurement reported as data — since the figure then carries information no word replaces. Keep an ordinal where a list orders or ranks its items, step 1 before step 2, the case of highest priority first, because position carries information. A count that only totals a set, "the four options", carries no rank and still drops.

One transitional phrase where the prose changes direction, none where it does not, and at most one per hundred words. Most paragraphs need none. Cut any that survives only because it sounds polished.

An em-dash interrupts or pivots, a colon announces, and a comma handles everything else. Hold to roughly one em-dash per paragraph. Reserve the semicolon for places no other punctuation works.

Prefer silence to restatement. Once the point lands, stop.

When list items act as sections someone skims between, promote them to headings. A heading enters the table of contents where a static analysis tool can check it, while a `**Term** — …` list item escapes both. Consider the bolded list only after headings, and keep it for items that stay short, parallel, and read in place.
