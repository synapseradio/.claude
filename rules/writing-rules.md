---
paths:
  - "**/rules/*.md"
  - "**/rulesets/-render/*.md"
  - "**/CLAUDE.md"
  - "**/SKILL.md"
  - "**/skills/**/*.md"
  - "**/.claude-plugin/*.json"
---

<!-- rule: writing-rules -->

## writing-rules

For every rules file, pool file, render, CLAUDE.md, skill file, and plugin you write or change, optimize for a reader who decides the same way every turn and holds every line as binding.

- stem: the filename without .md
- marker: `<!-- rule: stem -->` alone on its line at column 0
- opener: one sentence, "For every X" or "In every context and every turn", X the rule's whole scope, then "optimize for" one quality in one clause
- terms block: `- term: gloss` lines, each term with one sense, each gloss self-contained, its warrant left out
- shared term: a term the core-rules body glosses, the body the rulesets config's `defaults` give every context
- halt: a sentence bounding its paragraph's or section's acts: the act in place of the excluded one, as "Move a branch ref with `git reset --soft`."; "X only on Y."; "Keep X out of Y."; or "Treat X as no ground for Y."
- pool: `rulesets/rules/`, one file per rule, `<name>.md` its default form and `<name>@<variant>.md` a variant, each a complete body
- rulesets config: `rulesets/config.yaml`, whose references deliver pool files: `defaults` to every context, a condition block, keyed by its condition as `model haiku:` is, to each context its condition on model, agent, kind, tools, flag, or session matches, and a named set under `sets:` wherever a reference spreads it
- render: a file under `rulesets/-render/` that `render` writes, composed pool bodies each under its marker
- `$CLI`: `python3.15 features/plugins/rulesets/lib/rulesets/cli.py`, run from the repository root, each command closing on `--root rulesets`

Order a rules file: marker, one blank line, `## stem`, opener, terms block, instructions. Keep `paths:` frontmatter above the marker on a path-scoped rule, its globs matching file paths. Write a condition clause, "When you are X" for one, as an arm. Keep the case for the rule out of every paragraph.
Order a pool file as a rules file from `## stem` on, cutting the stem at any `@`. Keep the marker and frontmatter out of every pool file.

Set the instructions in short paragraphs or `###` sections, each on one concern. Give each definition of a kind its own paragraph. Map cases to acts in a guard block, an arm, or a switch, each arm and switch on its own line. Order a procedure's sentences as its steps run. Close each paragraph and section on its halts. Head a section with a `###` label where a scanning reader looks for it or other prose cites it. Fence only a template the model emits.

Write each line in the fewest words that keep its direction. Give each sentence one instruction. Write every directive as the act to take, turning a negation, "never" for one, into a halt.
The halt covers fewer cases than the negation ? name an act for each case it dropped.
Keep a contrast with what would otherwise happen beside the act it places. Write a fact as an instruction with a stance verb: hold, treat, read, count, or rely on. Write a vague qualifier, "short" for one, as a bound testable on the artifact, in place of a static count. Drop every numeral that sizes a listed set. Keep every threshold's number. Close every out: a departure rests only on the user's licence or a fact a reader can check.
A cut sentence described a failure mode ? write the halt or arm guarding against it.
A cut sentence carried a stance ? write the instruction enacting it.
Keep a fact only where an instruction cannot run without it, a config path for one.

Write every sentence blameless, free of any debt the reader or the user owes and any guess at what the reader holds or where they have been. Keep the writer out of the reader's view: a plain imperative to the reader stays, and the writer's attitude toward the reader goes. Let a person appear as a source or as someone the practice serves. Keep intensifiers out, "CRITICAL" for one. Hold a rule as a prompt rather than source: state the objective and the bounds, and let the reader carry the act.

Let each line below the terms block state a test runnable on the artifact or a stance the reader holds. Gloss every term the file coins in its terms block, and use a shared term in place of a gloss of your own. State a class of cases by its generating mechanism, one example at most. Give each instruction one home. Keep every rule distinct and standing on its own text plus the shared terms, naming and linking no other rule or rules file.
Keep every name the governed repository's source defines, a file path, a function, a variable, or a command, out of a rule, keeping only a command or config path an instruction cannot run without, and state the principle each name left out served.
A term a body coins collides with a shared term or with a term another body coins ? rename it or qualify it into a longer phrase.

### Routing

Route content before writing it.

placing content
  | an invariant every context holds = a pool file the rulesets config's `defaults` reach
  | a term or notation two or more bodies lean on = the core-rules terms block
  | an invariant for one kind of file = a path-scoped file under `rules/`
  | differs by model or another context fact = a variant file in the pool,
      a complete body, set by a condition block testing that fact
  | an invariant some contexts hold = a pool file, referenced from the
      named set or condition block whose contexts hold it
  | a catalog = `references/`
  | an instruction only one tool's workflow acts on = that tool's own config,
      in the slot whose reader acts when it applies, chosen after reading
      the tool's customization docs at the installed version
  | enforcement a mechanical test decides = a hook
  | enforcement that needs a judgment, whether a claim carries weight for one
      = an instruction in the rule whose object it concerns
  | stance = an instruction in the rule whose object it concerns;
      CLAUDE.md carries the user's greeting alone
  | otherwise = ask the user where it goes

A doc page would restate an instruction a tool's config holds ? link the config.
Write a hook's message as the act it asks of its reader.

### Changing a rule

Hold every line of an existing rule as written against a failure seen in practice. Change a rule on the user's instruction or on cited evidence, a primary text by URL for one. Change a rule by adding or sharpening lines, keeping every touched directive's meaning. Write every change to a rules file, a pool file, or an agent file through an opus agent. Apply, through a haiku agent, text the user approved or a codemod that carries out a decision the user made. Weigh a change by the outputs the rule steers, in place of the work it asks of an agent.
Two rules overlap ? delegate `thinkies:survey-peers` on the overlapping lines to an opus agent, one overlap group per agent, one agent at a time -> rewrite the surveyed lines into rules with distinct jobs, every directive's meaning kept.
Merge two pool rules only where every context receives both or neither, checked with `$CLI explain` on each.
Evidence points at removing a line ? ask the user in its own question, with that evidence.
Treat a line's apparent idleness as no ground for removing it. Remove a line only on the user's approval.

### Syncing the render

Hold a variant file as the body replacing its default form in each context the rulesets config sets that variant for, and the default form as the body every other context receives. Leave CLAUDE.md unmarked. Edit whichever side is in hand, a pool file or its section of a render, keeping the render's marker lines. Edit a render only to `split` it back.
The edit landed in a render ? run `$CLI split <render>` before any `render` run.
`split` refuses ? repair the marker lines its message names -> run again.
A pool or rulesets config edit finished ? run `$CLI render` -> run `$CLI check` -> clear every error it reports.
A full-pass rewrite finished ? account for every line the diff against HEAD removes, before regenerating.
Edit a rules file one tool call per step.
Adding or removing a pool rule ? update the rulesets config's references to it in the same change -> confirm with `$CLI explain <name>`, given each served context's `--model`, `--agent`, and `--kind`, that the rulesets config delivers it there.
Renaming a rules file or a section another file cites ? sweep the citations in the same change.

### Skills and plugins

Keep every name of another skill, a harness, a ruleset, a vendor, a product, a model, and a machine path out of a skill's files, writing each needed instruction inline. List abilities in a skill's `compatibility` field, with product names kept out. Before packaging a skill, search it for other skills' names and for vendor and model names.

Keep authors, works, years, URLs, and attributed quotes out of a skill's files, README install and license links aside. Write each teaching example yourself as a contrast: the quality, an antipattern showing only the failure, a pattern showing only the target on the same content where possible, then what differs, what both keep, the one variable, and the signal to look for in a draft. Let a passage describing a target quality perform it. Keep a short "such as" list inside a question inline.

Ship in a plugin the mechanism alone, with every credential, private path, account identifier, and credential helper kept out, and every piece of its author's own content, a rule body, a pinned model identifier, or a generated render for one. Give a plugin a scaffold command where a corpus would ship, and keep it working on an empty corpus and for a second person who installs it owning nothing. Build every plugin test's fixtures synthetic in a temporary directory, with the real configuration tree kept out. Validate a credential helper by its existence, executability, and mode alone, with every run of it kept out. Before writing a plugin file, name the layer that catches a leak and the one command a reviewer runs to check it.

Keep a plugin working for a stranger who brings a configuration of their own, customizable through the override points it documents, a user-owned file or an environment variable. Keep the user's own settings, rules, and files out of every plugin's reads and assumptions. Treat a plugin's covering a setting as no ground for dropping, loosening, or reshaping that setting, and a fit with one configuration as no ground for changing a plugin.
Before editing a plugin or pruning a setting it overlaps, check whether the change behaves the same under another configuration -> where it differs, move the user-specific part into the user's own files or the plugin's override point.
