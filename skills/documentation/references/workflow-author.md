# Workflow: Author Documentation

<!--
execution: inline
parallelism: sequential
needs-user-interaction: false
-->

## Role

Document author. Produce a doc in exactly one Diátaxis quadrant, cited and style-compliant.

## Task

Write a new technical or conceptual doc for the subject named by the user. Classify the doc before drafting. Cite every external claim.

## Onboarding

Before drafting, load and read:

1. `references/diataxis-taxonomy.md` — classify the doc.
2. `references/writing-by-type.md` — pull the per-quadrant rules.
3. `references/voice-and-style.md` — voice and forbidden words.
4. `references/sourcing-and-citations.md` — citation rule.
5. If writing a mental-model or conceptual doc, also load `references/explanation-craft.md`.
6. If the doc includes diagrams, tables, or screenshots, also load `references/info-design-diagrams.md`.

## Process

Use `TaskCreate` to track each step as a task before beginning. The loop is six steps; do not skip any.

1. **Identify the subject and the reader's need.** State in one sentence: *who is reading, what do they need, what will they do with the doc?*
2. **Classify the quadrant.** Apply the Diátaxis compass from `diataxis-taxonomy.md`: *action or cognition? acquisition or application?* Record the answer before drafting.
3. **Pull the quadrant's rules.** From `writing-by-type.md`, copy the matching quadrant's "Do / Do not" list into your working notes. If the quadrant is *explanation*, also pull from `explanation-craft.md`.
4. **Draft.** Follow voice rules from `voice-and-style.md`. Attach a URL to every external claim in the same sentence. Keep warnings and caveats — do not omit them for cleanliness.
5. **Self-review with the rubric.** Run `references/review-rubric.md` against the draft. Every failure is a revision task.
6. **Verify.** Run `scripts/find-forbidden-words.sh <path-to-draft>`. If links are present, run `scripts/check-doc-links.sh <path-to-draft>`. Triage hits; do not blindly delete.

## Success Conditions

- The draft sits in exactly one Diátaxis quadrant. The classification is stated at the top of the working notes.
- Every external claim has a URL attached.
- `find-forbidden-words.sh` exits zero, or each hit is triaged and justified in writing.
- `check-doc-links.sh` exits zero, or every non-zero hit is noted with a reason.
- The draft passes the `review-rubric.md` checklist for its quadrant's section.

## Why

The Diátaxis framework observes that most documentation pain comes from conflating quadrants (see https://diataxis.fr/map/). Classifying before drafting is the single highest-leverage intervention. Citing every external claim is the single most effective rot mitigation (see https://scribelet.app/blog/outdated-documentation). This workflow composes both.
