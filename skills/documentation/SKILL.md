---
name: documentation
description: >-
  This skill should be used when the user asks to write, review, audit, refresh, or classify technical or conceptual documentation. Trigger phrases include "write docs for X", "write a tutorial / how-to / reference / explanation", "document this system / API / module / concept", "explain this system" (mental-model docs), "review these docs", "audit the documentation", "is this doc good", "fix stale docs", "refresh the documentation", "these docs are out of date", "classify this doc", "is this a tutorial or a how-to". Grounded in the Diátaxis four-quadrant taxonomy, Google / Microsoft / GitLab / Django style guides, Raymond's Unix-documentation honesty rule, Knuth's docs-as-literature spirit, Tufte's data-ink principle, and docs-as-code rot prevention. Every rule in the skill traces to a primary source URL.
---

# Documentation

Classify, write, review, and maintain technical and conceptual documentation. Grounded in the Diátaxis framework (https://diataxis.fr/) and the converging style rules of major developer-documentation style guides.

## Do not load for

- Passive reads of a README or existing doc (nothing to produce).
- Generating API docs from source code — use a doc-generator tool instead.
- Editing code comments in-flight during a code task.
- Marketing, blog, essay, or other non-technical prose.

If the task is one of the above, stop and tell the user the skill does not apply.

## The loop

The skill runs one of three procedures, always on the same three-step loop:

1. **Classify** — pick one Diátaxis quadrant (tutorial, how-to, reference, explanation) for the doc in hand.
2. **Do** — draft, review, or maintain, using the per-quadrant rules.
3. **Verify** — cite every external claim; run the forbidden-words scan; run the link-checker.

## Context loading

Load only the references the task requires. Each reference file is self-contained: load one, follow its URLs, apply its rules.

| If the task is... | Load | Skip |
|-------------------|------|------|
| Writing new docs | `references/diataxis-taxonomy.md`, `references/writing-by-type.md`, `references/voice-and-style.md`, `references/sourcing-and-citations.md`, `references/workflow-author.md` | `review-rubric.md`, `workflow-review.md`, `workflow-maintain.md` |
| Writing conceptual or mental-model docs | Above, plus `references/explanation-craft.md` | same |
| Reviewing an existing doc | `references/review-rubric.md`, `references/voice-and-style.md`, `references/workflow-review.md` | writing references |
| Maintaining docs / fighting rot | `references/rot-prevention.md`, `references/workflow-maintain.md` | writing references |
| Adding diagrams, tables, screenshots | `references/info-design-diagrams.md` | everything else |
| Classifying a doc only | `references/diataxis-taxonomy.md` | everything else |

The `examples/` directory contains one short exemplar per quadrant. Read them when drafting if a reference file alone leaves the shape unclear.

## Core procedure

Apply whether writing, reviewing, or maintaining:

1. **Classify against the Diátaxis compass before writing or editing.** Ask: *action or cognition? acquisition or application?* (See `references/diataxis-taxonomy.md`.)
2. **Pick the matching quadrant's rules from `references/writing-by-type.md`.** Tutorials minimise explanation. How-to guides assume competence. Reference describes — it does not instruct or explain. Explanation weaves connections and answers *why*.
3. **Write in the voice described in `references/voice-and-style.md`.** Active voice. Second person. Present tense. Serial comma. Avoid the forbidden words.
4. **Cite every external claim** per `references/sourcing-and-citations.md`. API signatures, versions, limits, vendor behaviour — all need a resolvable URL.
5. **Run the scripts before declaring done:**
   - `scripts/find-forbidden-words.sh <path>` — fails if any diminishing words are present.
   - `scripts/check-doc-links.sh <path>` — wraps `lychee` if installed; prints an install hint if not.

## Task tracking

For any job that touches 3 or more files, or follows a 3-or-more-step workflow, use `TaskCreate` to track each step before starting work. The three workflow references (`workflow-author.md`, `workflow-review.md`, `workflow-maintain.md`) each define a task breakdown.

## Output formats

- **Writing** — markdown doc file(s), one Diátaxis quadrant per file. Name the quadrant in the doc title or a front-matter tag.
- **Reviewing** — a structured report with findings grouped by rubric category from `references/review-rubric.md`, each finding citing the source URL of the rule it invokes.
- **Maintaining** — a maintenance-action plan listing owner, last-verified date, link-checker output, and the list of external claims to re-verify.

## Rules

These rules take precedence over stylistic preference:

- **Never cite a source that isn't in this skill's reference files.** If a user asks for a rule this skill does not cite, say "The skill has no cited source for X" rather than inventing one.
- **Never attribute a rule to Axel Rauschmayer, Julia Evans, or Simon Willison.** No primary source was fetched for them during the research that grounds this skill.
- **When writing a citation, quote verbatim from the reference file; do not rephrase quoted text.** Paraphrases decay. The reference files carry the original blockquotes.
- **Never fabricate a URL.** Every URL in skill output must appear in a reference file inside this skill.
- **The forbidden-words list is aggressive and heuristic.** Triage results; do not blindly fix every hit.
- **When a doc mixes quadrants, flag the mix — do not merge them.** Conflating quadrants is the single most documented anti-pattern in the source material (Diátaxis map page).
- **Never remove a warning or functional detail from a doc to make it look cleaner.** Raymond's rule: "never ever omit functional details because you fear they might be confusing, nor warnings about problems because you don't want to look bad."
