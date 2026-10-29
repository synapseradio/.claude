---
paths:
  - "**/rules/*.md"
  - "**/rulesets/*/*.md"
  - "**/rulesets/renders/*/working-rules.md"
  - "**/CLAUDE.md"
---

<!-- rule: writing-rules -->

## writing-rules

For every rules file, rulesets tier body, working-rules render, and CLAUDE.md you write or change, optimize for a reader who decides the same way every turn and holds every line as binding.

- stem: the filename without .md
- marker: `<!-- rule: stem -->` alone on its line at column 0
- opener: one sentence, "For every X" or "In every context and every turn", X the rule's whole scope, then "optimize for" one quality in one clause
- terms block: `- term: gloss` lines, each term with one sense, each gloss self-contained, its warrant left out
- shared term: a term the core-rules body glosses, the body every tier delivers first
- halt: a sentence bounding its paragraph's or section's acts: the act in place of the excluded one, as "Move a branch ref with `git reset --soft`."; "X only on Y."; "Keep X out of Y."; or "Treat X as no ground for Y."
- renderer: `resolve.py render`, from the installed model-scoped-rulesets plugin, syncing the bodies under `~/.claude/rulesets/$tier/` plus CLAUDE.md with `~/.claude/rulesets/renders/$tier/working-rules.md` both ways, keyed on markers, ordered by the `order:` list in `~/.claude/rulesets/manifest.yaml`
- render section: a marker through the next marker or the end of the file
- preamble: a render's text between its title and first marker, the text CLAUDE.md holds

Order a rules file: marker, one blank line, `## stem`, opener, terms block, instructions. Keep `paths:` frontmatter above the marker on a path-scoped rule, its globs matching file paths. Write a condition clause, "When you are X" for one, as an arm. Keep the case for the rule out of every paragraph.

Set the instructions in short paragraphs or `###` sections, each on one concern. Map cases to acts in a guard block, an arm, or a switch, each arm and switch on its own line. Order a procedure's sentences as its steps run. Close each paragraph and section on its halts. Head a section with a `###` label where a scanning reader looks for it or other prose cites it. Fence only a template the model emits.

Write each line in the fewest words that keep its direction. Give each sentence one instruction. Write every directive as the act to take, turning a negation, "never" for one, into a halt.
The halt covers fewer cases than the negation ? name an act for each case it dropped.
Keep a contrast with what would otherwise happen beside the act it places. Write a fact as an instruction with a stance verb: hold, treat, read, count, or rely on. Write a vague qualifier, "short" for one, as a bound testable on the artifact, in place of a static count. Drop every numeral that sizes a listed set. Keep every threshold's number. Close every out: a departure rests only on the user's licence or a fact a reader can check.
A cut sentence described a failure mode ? write the halt or arm guarding against it.
A cut sentence carried a stance ? write the instruction enacting it.
Keep a fact only where an instruction cannot run without it, a config path for one.

Write every sentence blameless, free of any debt the reader or the user owes and any guess at what the reader holds or where they have been. Keep the writer out of the reader's view: a plain imperative to the reader stays, and the writer's attitude toward the reader goes. Let a person appear as a source or as someone the practice serves. Keep intensifiers out, "CRITICAL" for one. Hold a rule as a prompt rather than source: state the objective and the bounds, and let the reader carry the act.

Let each line below the terms block state a test runnable on the artifact or a stance the reader holds. Gloss every term the file coins in its terms block, and use a shared term in place of a gloss of your own. State a class of cases by its generating mechanism, one example at most. Give each instruction one home. Keep every rule distinct and standing on its own text plus the shared terms, naming and linking no other rule or rules file.
A term a body coins collides with a shared term or with a term another body coins ? rename it or qualify it into a longer phrase.

### Routing

Route content before writing it.

placing content
  | an always-on invariant = `rulesets/default/`, and from there every tier
  | a term or notation two or more bodies lean on = the core-rules terms block
  | an invariant for one kind of file = a path-scoped file under `rules/`
  | differs for one model = that model's tier directory, as an override of the same stem
  | a catalog = `references/`
  | enforcement = a hook
  | stance = an instruction in the rule whose object it concerns;
      CLAUDE.md carries the user's greeting alone
  | otherwise = ask the user where it goes

### Changing a rule

Hold every line of an existing rule as written against a failure seen in practice. Change a rule on the user's instruction or on cited evidence, a primary text by URL for one. Change a rule by adding or sharpening lines, keeping every touched directive's meaning. Write every change to a rules file, a ruleset body, or an agent file through an opus agent. Apply, through a haiku agent, text the user approved or a codemod that carries out a decision the user made. Weigh a change by the outputs the rule steers, in place of the work it asks of an agent.
Two rules overlap ? delegate `thinkies:survey-peers` on the overlapping lines to an opus agent, one overlap group per agent, one agent at a time -> rewrite the surveyed lines into rules with distinct jobs, every directive's meaning kept.
Merge two bodies only where every tier's `exclude` list holds both or neither.
Evidence points at removing a line ? ask the user in its own question, with that evidence.
Treat a line's apparent idleness as no ground for removing it. Remove a line only on the user's approval.

### Syncing the render

Hold a body under a tier directory other than `default/` as that tier's override. Hold every other stem of a tier as composed from `default/`. Leave CLAUDE.md unmarked. Edit whichever side is in hand -> run the renderer toward the other.
The run refuses on an uncommitted target ? restore it with `git checkout HEAD -- <path>` -> run again.
A reverse run finished ? render every tier -> run `resolve.py check`.
A full-pass rewrite finished ? account for every line the diff against HEAD removes, before regenerating.
Edit a rules file one tool call per step.
Adding or removing an always-on rule ? change the `order:` list in the same change.
Renaming a rules file or a section another file cites ? sweep the citations in the same change.
