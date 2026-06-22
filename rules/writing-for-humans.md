# Writing for Humans

This rule is in force whenever the task puts natural language on the page. It governs ANY writing that is not executable code: documentation, comments in source files, commit messages, PR and ticket descriptions, design docs, chat replies, and every other kind of prose.

You must read [writing-for-humans-reference.md](../references/writing-for-humans-reference.md) in full before you write any of it — every entry of the TIER 1 hard bans and the TIER 2 active preferences, never a remembered summary. The full read is mandatory and not optional. A partial read, or a recollection of an earlier one, does not satisfy this rule.

Value simplicity, clarity, conciseness and relevance.

Write for a human reader who may not share your native language.

Write unambiguously in a tone that matches the role, audience, and current content of what you are writing.

Use concrete words rather than jargon or idiom.

Write complete sentences and punctuate correctly.

Keep the voice calm and clear, with light humor permitted.

State what something does. Never reach for the negation–affirmation mirror — "not X; Y", "did not A; it B'd", "not just Y but Z" — which stages a reversal in place of information. Lead with the affirmative and cut the negated half. This is a TIER 1 hard ban; see the reference for every form.

Prefer qualitative quantifiers to scalars in prose. A precise count binds the sentence to a number that drifts and usually reads false by the time someone reaches it, while words like "some", "most of", and "far more" carry the inequality, contrast, or scale you actually meant to show. Keep an exact figure only when the figure is itself the subject, such as an identifier, a version, a limit, or a measurement being reported as data.

End a paragraph when the thought ends.

If a sentence performs rather than informs, rewrite it plainly.

When registers clash, surface the mismatch rather than smoothing it over.

Be attentive to structure. Well-structured thoughts lead to clear writing. Structure also means sensitivity to typesetting and file format; markdown asks for syntax structure in prose that comments or other file types would not. Reach for a real heading before a bolded lead-in on a list item: a heading is part of the document structure a reader skims and a static analysis tool can check, where a bolded list item is neither. See [progressive-enhancement.md](./progressive-enhancement.md) for when a bolded lead-in still earns its place.
