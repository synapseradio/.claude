# Review Rubric

A checklist for auditing an existing doc. Each item names a rule, the source that grounds it, and the failure mode it catches. One criterion per line.

## How to use this file

Run the rubric top-to-bottom on each doc under review. For each item, mark **pass**, **fail**, or **n/a**. Every **fail** citation in the output report cites the rule's source URL.

## Primary sources

| URL | Topic |
|-----|-------|
| <https://diataxis.fr/map/> | Category conflation |
| <https://diataxis.fr/tutorials/> | Tutorial discipline |
| <https://diataxis.fr/how-to-guides/> | How-to discipline |
| <https://diataxis.fr/reference/> | Reference discipline |
| <https://diataxis.fr/explanation/> | Explanation discipline |
| <https://developers.google.com/style/voice> | Active voice |
| <https://developers.google.com/style/tone> | Google tone — forbidden words |
| <https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/> | Django diminishing-words rule |
| <https://docs.gitlab.com/development/documentation/styleguide/> | Single source of truth |
| <https://learn.microsoft.com/en-us/style-guide/top-10-tips-style-voice> | Microsoft top 10 |
| <http://www.catb.org/~esr/writings/taoup/html/ch18s06.html> | Raymond — never omit warnings; screenshot caution |
| <https://scribelet.app/blog/outdated-documentation> | External-claim drift |
| <https://www.edwardtufte.com/book/the-visual-display-of-quantitative-information/> | Tufte — data-ink / chartjunk |
| <https://radicalresearch.llc/EA078_Fall2024/chartJunk.html> | Quoted Tufte definition |
| <https://thegooddocsproject.dev/> | Template-and-checklist movement |
| <https://slab.com/blog/stripe-writing-culture/> | Stripe — sample docs beat blank templates |

## 1. Classification (Diátaxis)

- [ ] The doc is classifiable as exactly one of: tutorial, how-to, reference, explanation. — <https://diataxis.fr/>
- [ ] The doc does not conflate tutorial and how-to. — <https://diataxis.fr/map/> ("In the worst case there is a complete or partial collapse of tutorials and how-to guides into each other")
- [ ] Reference material does not instruct or explain. — <https://diataxis.fr/reference/>
- [ ] Tutorial does not explain. — <https://diataxis.fr/tutorials/> ("Explanation distracts their attention from that, and blocks their learning")
- [ ] Explanation does not walk through a first run. — <https://diataxis.fr/explanation/>

## 2. Per-quadrant discipline

- [ ] **Tutorial**: reader reaches a concrete result early. — <https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/> ("help the reader achieve something useful, preferably as early as possible")
- [ ] **How-to**: assumes competence; omits the unnecessary. — <https://diataxis.fr/how-to-guides/>
- [ ] **Reference**: adopts a single structural pattern across entries. — <https://diataxis.fr/reference/> ("Standard patterns are what allow us to use reference material effectively")
- [ ] **Explanation**: makes connections, provides background, answers *why*. — <https://diataxis.fr/explanation/>

## 3. Voice and style

- [ ] Active voice is the default. — <https://developers.google.com/style/voice>
- [ ] Second person, present tense. — convergent across Google, Microsoft, GitLab.
- [ ] Contractions used; serial comma applied. — <https://learn.microsoft.com/en-us/style-guide/top-10-tips-style-voice>
- [ ] No diminishing words (*simply, easily, just, merely, straightforward, quickly, obviously, clearly*) in non-quoted prose. — <https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/> and <https://developers.google.com/style/tone>
- [ ] No placeholder phrases (*please note*, *at this time*). — <https://developers.google.com/style/tone>
- [ ] No exclamation marks, internet slang, wackiness. — <https://developers.google.com/style/tone>

## 4. Sourcing and clarity

- [ ] Every claim about an external system has a resolvable URL in the same sentence or adjacent to it. — <https://scribelet.app/blog/outdated-documentation> (external-claim drift)
- [ ] Warnings and functional details are not omitted for cleanliness. — <http://www.catb.org/~esr/writings/taoup/html/ch18s06.html> ("never ever omit functional details because you fear they might be confusing, nor warnings about problems because you don't want to look bad")
- [ ] URLs point at primary sources, not aggregators.
- [ ] Where the source is unknown or uncertain, the doc says so explicitly.

## 5. Staleness

- [ ] Link checker (e.g., `scripts/check-doc-links.sh`) has been run and passes.
- [ ] Cited external-system behaviours match current primary sources (re-fetch and compare).
- [ ] A named owner is identifiable for the doc. — <https://scribelet.app/blog/outdated-documentation>
- [ ] Doc does not contradict the single source of truth. — <https://docs.gitlab.com/development/documentation/styleguide/> ("Documentation is the single source of truth")

## 6. Information design

- [ ] Each diagram's marks each carry data. — <https://www.edwardtufte.com/book/the-visual-display-of-quantitative-information/> ; <https://radicalresearch.llc/EA078_Fall2024/chartJunk.html>
- [ ] Tables have no decorative-only columns.
- [ ] Screenshots are used only where text cannot convey the information. — <http://www.catb.org/~esr/writings/taoup/html/ch18s06.html> ("They are never a good substitute for clear textual description")

## 7. Shipping essentials

For project-level docs (README, landing page):

- [ ] States what problem the project solves. — <https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/>
- [ ] Small code example.
- [ ] Install instructions.
- [ ] Link to code and issue tracker.
- [ ] How to get support.
- [ ] How to contribute.
- [ ] License.

## Stripe / culture appendix

Some cultural practices do not belong to a single rule but inform the whole skill. Stripe's documentation manager names one:

> "We create docs that offer some of the basics, so engineers aren't forced to stare at a blank page — which can be terrifying."
>
> — <https://slab.com/blog/stripe-writing-culture/>

And:

> "Stripe has similar sample docs for READMEs, runbooks, and FAQs. Nunez believes these sample documents are more useful than fill-in-the-blank templates, because they provide readers more context and content to work with."
>
> — same URL

Implication for review: when a team lacks docs in a quadrant, the highest-leverage move is to ship a *concrete sample doc in that quadrant*, not a fill-in-the-blank template. The `examples/` directory in this skill applies the same pattern.

And on writing as thinking, attributed to Stripe leadership:

> "Writing forces you to structure your thoughts in a manner just not possible when you verbalize it. When I write, I have to offer structured, precise thoughts."
>
> — <https://slab.com/blog/stripe-writing-culture/>

## Report format

When producing a review output, group findings by the section numbers above. Each finding names the failed criterion, the cited source URL, and the specific line or passage in the doc. Do not merge findings across sections.

## Agent instructions

1. Before reviewing, load `voice-and-style.md`, `diataxis-taxonomy.md`, and `sourcing-and-citations.md`.
2. Run the rubric top-to-bottom in order. Do not skip sections.
3. Every failure in the report cites the source URL, not this rubric file.
4. Distinguish confirmed failures from suspected ones. Mark the suspected with `[?]`.
5. For each forbidden-word hit, read the context before flagging. Some are legitimate.
