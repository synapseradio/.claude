# Diátaxis Taxonomy

Classify any technical or conceptual doc into one of four quadrants: **tutorial**, **how-to guide**, **reference**, or **explanation**. The Diátaxis framework (Daniele Procida) posits that these four needs are distinct and that conflating them is the primary cause of documentation pain.

## Primary sources

| URL | Topic |
|-----|-------|
| https://diataxis.fr/ | Framework home |
| https://diataxis.fr/tutorials/ | Tutorials quadrant |
| https://diataxis.fr/how-to-guides/ | How-to guides quadrant |
| https://diataxis.fr/reference/ | Reference quadrant |
| https://diataxis.fr/explanation/ | Explanation quadrant |
| https://diataxis.fr/compass/ | The compass — how to classify |
| https://diataxis.fr/map/ | The map — analogies and anti-patterns |
| https://diataxis.fr/foundations/ | Why four and not three or five |
| https://diataxis.fr/quality/ | Functional vs. deep quality |
| https://documentation.divio.com/introduction/ | Divio's earlier presentation of the same taxonomy |
| https://2017.pycon-au.org/schedule/presentation/15/ | Procida's PyCon AU 2017 talk abstract |

## The four needs

> "Diátaxis identifies four distinct needs, and four corresponding forms of documentation — tutorials, how-to guides, technical reference and explanation. It places them in a systematic relationship, and proposes that documentation should itself be organised around the structures of those needs."
>
> — https://diataxis.fr/

Divio states the same finding in its introduction:

> "There is a secret that needs to be understood in order to write good software documentation: there isn't one thing called documentation, there are four. They are: tutorials, how-to guides, technical reference and explanation. They represent four different purposes or functions, and require four different approaches to their creation."
>
> — https://documentation.divio.com/

## The compass

Classify by asking two questions, in order.

> "Two questions need to be asked: action or cognition? acquisition or application?"
>
> — https://diataxis.fr/compass/

The compass then produces the quadrant:

| The user is... | ...and needs... | The doc is a |
|----------------|------------------|--------------|
| taking action | to **acquire** a skill | **Tutorial** |
| taking action | to **apply** a skill | **How-to guide** |
| thinking | to **apply** a skill | **Reference** |
| thinking | to **acquire** a skill | **Explanation** |

Source: https://diataxis.fr/compass/

## The map — analogies that anchor each quadrant

> Tutorial: "teaching a child how to cook"
> How-to: "a recipe in a cookery book"
> Reference: "information on the back of a food packet"
> Explanation: "an article on culinary social history"
>
> — https://diataxis.fr/map/

Use these analogies as a final check after the compass pick. If the draft in hand does not feel like the analogy, the quadrant is probably wrong.

## Why exactly four

> Diátaxis derives the four quadrants from two orthogonal axes (action/cognition; acquisition/application of skill) that "cover the entire territory" of craft; therefore "there are necessarily four quarters to it."
>
> — https://diataxis.fr/foundations/

Do not add a fifth category. Do not collapse two. The axes are orthogonal by construction.

## Quality has two layers

> "Diátaxis addresses deep quality" — the layer beneath the measurable functional quality of a doc (accuracy, completeness, consistency, usefulness, precision). Deep quality is "subjective, interdependent, assessed against the human."
>
> — https://diataxis.fr/quality/

Implication: a doc can be factually accurate (functional quality) yet fail its reader (deep quality) if it is in the wrong quadrant.

## The chief anti-pattern: conflation

> "In the worst case there is a complete or partial collapse of tutorials and how-to guides into each other, making it impossible to meet the needs served by either."
>
> — https://diataxis.fr/map/

When classifying an existing doc, look specifically for tutorial / how-to conflation. It is the single most frequent failure mode named in the source material.

## Procida's stance on publishing cadence

> "projects demand plans, but complex projects lure us into creating complicated plans. Until we have finished executing our plans, we won't have anything useful to show for our efforts."
>
> — https://www.knowledgeowl.com/blog/posts/always-complete-never-finished (summary of Procida's Write the Docs talk; the PyCon AU 2017 abstract is the nearest primary-source companion: https://2017.pycon-au.org/schedule/presentation/15/)

See `rot-prevention.md` for the "always complete, never finished" frame in full.

## Agent instructions

1. Before writing or editing a doc, ask the two compass questions and record the answer.
2. If the doc resists classification, it is probably two docs. Split it before writing.
3. Cite the specific Diátaxis sub-page URL when applying a quadrant rule — `https://diataxis.fr/tutorials/` for tutorial-discipline claims, not a generic link.
4. Before trusting a rule from this file, fetch the source URL and confirm the quoted text still appears. Diátaxis is a living document; updates happen.
