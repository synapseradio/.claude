# Evergreen Artifacts: No Transitional Framing

See also: [progressive-enhancement.md](./progressive-enhancement.md).

<when> writing code comments, SKILL.md, commands/*.md, agents/*.md, plugin READMEs, reference docs — any prose that describes what a thing IS.

<never> Encode *when* something was true or *what comes next* in an evergreen artifact. No "migration in progress" banners. No "(intended surface)." No "will be implemented in Phase 2." No "superseded as of <date>." No "does not currently execute pending rewrite."

<always> Document current state as fact. A reader six months from now, with no memory of the project's history, must not be confused or misled.

<prefer> Good code comments explain what is, why it is, and what matters for consideration if changes happen — never transitional state.

### Pattern

Bad: "Migration in progress — the X CLI was removed pending a rewrite. The commands below describe the intended surface."
Good: "X exposes the following commands:" (If a command does not exist yet, do not document it yet.)

Bad: "Phase 2 will add validation; for now this accepts any input."
Good: Document what the function accepts today. Track the gap in an issue, not the doc.

### Exclusions

Temporal framing is correct in: CHANGELOGs, MIGRATION_SPEC.md, release docs, commit messages, PR descriptions, issue bodies, and archival status labels ("Archived YYYY-MM-DD; retained as history").

<never> Add a banner to an evergreen artifact because a plan instructs you to.
<always> Ask before adding it.
