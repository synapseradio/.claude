# Evergreen Artifacts: No Transitional Framing
@./progressive-enhancement.md
Applies when writing or modifying an evergreen artifact — code comments, SKILL.md, commands/*.md, agents/*.md, plugin READMEs, reference docs, or any prose that describes what a thing IS.

- **No transitional framing.** Evergreen artifacts describe current state as a fact. Do not encode *when* something was true or *what comes next* into them. No "migration in progress" banners, no "(intended surface)", no "will be implemented in Phase 2", no "superseded as of <date>", no "does not currently execute pending rewrite." These are temporal pollution; they rot the moment the migration lands.
- **Test:** would a reader six months from now, with no memory of this migration, be confused or misled by the sentence? If yes, rewrite evergreen or delete.
- **Pattern:**
  - Bad: "Migration in progress — the X CLI was removed pending a rewrite. The commands below describe the intended surface."
  - Good: "X exposes the following commands:" (If a command does not exist yet, do not document it yet.)
  - Bad: "Phase 2 will add validation; for now this accepts any input."
  - Good: Document what the function accepts today. Track the gap in an issue, not the doc.
- **Exclusions (temporal is the topic, keep it):** CHANGELOGs, MIGRATION_SPEC.md and release/contract docs, commit messages, PR descriptions, issue bodies, archival status labels on historical documents ("Archived YYYY-MM-DD; retained as history").
- **If the plan you are following tells you to add a banner,** the plan is wrong on this point. Ask before adding it.
- Good code comments explain what is, why it is, and what matters for consideration if changes are to happen — never transitional state.
