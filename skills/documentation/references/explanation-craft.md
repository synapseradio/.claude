# Explanation Craft

The explanation quadrant is the hardest to write. This file collects the primary-source guidance on *how* to do it, and what distinguishes explanation from tutorial, how-to, and reference.

## Primary sources

| URL | Topic |
|-----|-------|
| https://diataxis.fr/explanation/ | Diátaxis explanation quadrant |
| https://diataxis.fr/map/ | Analogy: "an article on culinary social history" |
| https://www-cs-faculty.stanford.edu/~knuth/lp.html | Knuth's literate programming page |
| https://en.wikipedia.org/wiki/Literate_programming | Wikipedia's sourced Knuth quotes |

## What explanation is

> "When writing explanation you are helping to weave a web of understanding for your readers. Make connections to other things, even to things outside the immediate topic, if that helps... Provide background and context in your explanation: explain *why* things are so — design decisions, historical reasons, technical constraints — draw implications, mention specific examples."
>
> — https://diataxis.fr/explanation/

This passage is the backbone of the quadrant. Treat it as the definition of the craft. The verbs that appear in the source are *weave*, *make connections*, *provide background*, *explain why*, *draw implications*, *mention examples*.

## The analogy

> Explanation: "an article on culinary social history."
>
> — https://diataxis.fr/map/

Test the draft against the analogy. An article on culinary social history does not list ingredients, does not recipe-walk the reader through a dish, and does not teach a novice to cook. It shows the reader how things came to be as they are, and why the current shape matters.

## What explanation is not

- Not a tutorial. No step-by-step walkthrough toward a first result.
- Not a how-to. No goal-shaped task instructions.
- Not reference. No parameter lists, API signatures, or exhaustive enumeration.

If the draft drifts into any of those, the quadrant is wrong or the doc is two docs.

## Docs-as-literature: the Knuth spirit

Literate programming is not the same as explanation docs, but its stance — that programs and documentation are written for humans, not just machines — anchors the explanation quadrant in a larger tradition.

> "Literate programming is a methodology that combines a programming language with a documentation language, thereby making programs more robust, more portable, more easily maintained, and arguably more fun to write than programs that are written only in a high-level language."
>
> — https://www-cs-faculty.stanford.edu/~knuth/lp.html

> "The main idea is to treat a program as a piece of literature, addressed to human beings rather than to a computer."
>
> — https://www-cs-faculty.stanford.edu/~knuth/lp.html

And the craft claim from Knuth, via Wikipedia:

> "Literate programming provides higher-quality programs, since it forces programmers to explicitly state the thoughts behind the program, making poorly thought-out design decisions more obvious."
>
> — https://en.wikipedia.org/wiki/Literate_programming

The transferable lesson for explanation docs: articulating the *why* surfaces weaknesses in the *what*. If explanation of a system is hard to write, the system is often hard to justify.

## Practitioner patterns (not doctrine)

The patterns below appeared in the research notes but were flagged as *not verified against a primary source*. They may be useful as starting heuristics, but they are not cited rules.

- **Lead with what is always true about the system** before the mechanics. No primary source was found for this as a prescribed rule for explanation docs; mentioned here as a practitioner pattern, not documented doctrine.
- **Progressive disclosure** (short summary first, detail behind a link). No primary source was found for this in the research underlying this skill; treat it as a pattern, not a citation.

Do not cite these as rules. If a consumer asks for a source, state: "No primary source was found for this; it is a practitioner pattern, not documented doctrine."

## Agent instructions

1. Before drafting an explanation, re-read the Diátaxis explanation quote above and list the five acts it names (*weave, make connections, provide background, explain why, draw implications*). The draft should visibly do each.
2. Identify at least one *design decision*, one *historical reason*, and one *technical constraint* for the subject. If the draft cannot name these, it is not yet an explanation.
3. Write examples into the explanation; do not save them for a separate reference or tutorial.
4. Cite https://diataxis.fr/explanation/ when stating an explanation-discipline rule. Cite the Knuth URL for the docs-as-literature stance.
5. Do not invent citations for the practitioner patterns in the last section; they are not cited here because no primary source was fetched.
