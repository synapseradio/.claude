# Writing by Type

Per-quadrant rules for drafting a new doc once it has been classified. Each quadrant has its own discipline — the rules do not transfer across the diagonal.

## Primary sources

| URL | Topic |
|-----|-------|
| https://diataxis.fr/tutorials/ | Tutorial discipline |
| https://diataxis.fr/how-to-guides/ | How-to discipline |
| https://diataxis.fr/reference/ | Reference discipline |
| https://diataxis.fr/explanation/ | Explanation discipline |
| https://diataxis.fr/map/ | Analogies and cross-quadrant anti-patterns |
| https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/ | Django's writing guide (tutorial + topic-guide advice) |
| http://www.catb.org/~esr/writings/taoup/html/ch18s06.html | Raymond on Unix documentation taxonomy |

## Tutorials

Analogy: **"teaching a child how to cook."** — https://diataxis.fr/map/

> "A tutorial is not the place for explanation. In a tutorial, the user is focused on correctly following your directions and getting the expected results... Explanation distracts their attention from that, and blocks their learning."
>
> — https://diataxis.fr/tutorials/

Django puts the same rule in a different voice:

> "The important thing in a tutorial is to help the reader achieve something useful, preferably as early as possible, in order to give them confidence... Don't feel that you need to begin with explanations of how things work — what matters is what the reader does, not what you explain."
>
> — https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/

### Do

- Give the reader a concrete win early.
- State each step as an imperative action the reader performs.
- Show the result the reader should see after each step.

### Do not

- Branch into alternative approaches.
- Explain *why* the step works (unless one sentence is needed for the reader to continue).
- Assume the reader already knows the domain.

## How-to guides

Analogy: **"a recipe in a cookery book."** — https://diataxis.fr/map/

> "In how-to guides, practical usability is more helpful than completeness... A how-to guide serves the work of the already-competent user."
>
> — https://diataxis.fr/how-to-guides/

### Do

- Assume competence. The reader has a goal and already knows the vocabulary.
- Address real-world complexity (alternatives, edge cases) where the goal demands it.
- Link to reference material rather than restate it.

### Do not

- Teach the basics of the tool.
- Pad with explanation the competent reader does not need.

Django reinforces the link-out rule for topic (how-to / conceptual) guides:

> "Link to reference material rather than repeat it. Use examples and don't be reluctant to explain things that seem very basic to you — it might be the explanation someone else needs."
>
> — https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/

## Reference

Analogy: **"information on the back of a food packet."** — https://diataxis.fr/map/

> "The only purpose of a reference guide is to describe, as succinctly as possible, and in an orderly way... Reference material is useful when it is consistent. Standard patterns are what allow us to use reference material effectively."
>
> — https://diataxis.fr/reference/

> Reference should "link to how-to guides, explanation and introductory tutorials" instead of absorbing their content.
>
> — https://diataxis.fr/reference/

### Do

- Describe. State what the thing is, what it accepts, what it returns, what it limits.
- Adopt a single structural pattern and hold it across every entry (e.g., every function entry has the same headings in the same order).
- Stay succinct.

### Do not

- Instruct (send the reader to a how-to).
- Explain (send the reader to an explanation).
- Break the structural pattern for any one entry, however special that entry feels.

Raymond adds a genre-specific discipline for Unix reference:

> "Your man pages should be command references in the traditional Unix style for the traditional Unix audience. The tutorial manual should be long-form documentation for nontechnical users. And the FAQ should be an evolving resource that grows as your software support group learns what the frequent questions are and how to answer them."
>
> — http://www.catb.org/~esr/writings/taoup/html/ch18s06.html

And cautions against over-length:

> "Huge man pages are viewed with some disfavor; navigation within them can be difficult."
>
> — same URL

## Explanation

Analogy: **"an article on culinary social history."** — https://diataxis.fr/map/

> "When writing explanation you are helping to weave a web of understanding for your readers. Make connections to other things, even to things outside the immediate topic, if that helps... Provide background and context in your explanation: explain *why* things are so — design decisions, historical reasons, technical constraints — draw implications, mention specific examples."
>
> — https://diataxis.fr/explanation/

This is the quadrant that most resists a checklist. See `explanation-craft.md` for the craft of writing explanations in depth.

### Do

- Make connections.
- Provide background and design history.
- Answer *why*.
- Draw implications.

### Do not

- Tell the reader what to do (that is a how-to).
- List parameters (that is reference).
- Walk the reader through a first run (that is a tutorial).

## Raymond's three-doc Unix taxonomy

A parallel, older framing that maps onto Diátaxis:

> "If your project is of any significant size, you should probably be shipping three different kinds of documentation: man pages as reference material, a tutorial manual, and a FAQ (Frequently Asked Questions) list."
>
> — http://www.catb.org/~esr/writings/taoup/html/ch18s06.html

Raymond's three roughly correspond to reference (man pages), tutorial (manual), and how-to (FAQ, which in practice answers goal-shaped questions). Diátaxis adds the fourth quadrant — explanation — that Raymond does not name.

## Honesty rule

Applies to every quadrant:

> "Don't think for a moment that volume will be mistaken for quality. And especially, never ever omit functional details because you fear they might be confusing, nor warnings about problems because you don't want to look bad. It is unanticipated problems that will cost you credibility and users, not the problems you were honest about."
>
> — http://www.catb.org/~esr/writings/taoup/html/ch18s06.html

## Agent instructions

1. Before drafting, confirm the quadrant via `diataxis-taxonomy.md`.
2. Pull the matching quadrant's "Do / Do not" list from this file.
3. When tempted to cross a line (e.g., explain inside a tutorial), re-read the blockquote for that quadrant and decide whether to split the doc.
4. Cite the specific sub-page URL when invoking a rule; cite Raymond's URL for the honesty rule.
