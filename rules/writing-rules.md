---
paths:
  - "**/rules/*.md"
  - "**/rulesets/*/*.md"
  - "**/rulesets/renders/*/working-rules.md"
  - "**/CLAUDE.md"
---

<!-- rule: writing-rules -->

## writing-rules

For every rules file, rulesets tier body, working-rules render, and CLAUDE.md you write or change, optimize for a rules file whose reader decides the same way every turn and holds every line as binding.

### The form

A rules file is markdown that opens on its marker, `<!-- rule: stem -->` alone on its line at column 0, where the stem is the filename without .md. One blank line follows the marker, then the title, `## stem`. A path-scoped rule keeps `paths:` frontmatter above the marker, with globs matching file paths. Below the title, the opener and then the machine make up the rest of the file.

The opener is one sentence. It names the rule's whole scope as a universal, "For every X" or "In every context and every turn", then "optimize for" and one quality in one clause. Open every rule on that universal. Move a condition, "When you are X" or "This rule applies when" for one, into an arm of the machine. Keep the case for the rule out of every paragraph.

The machine is a sequence of groups, each a paragraph or a `###` section. A definition group fixes terms, one per sentence, each self-contained, its warrant left out. A decision group is ordered arms, the first that fits winning, written "Where X, Y." or "When X, Y.", with "Otherwise, Z." last, as bullets where the arms are many. A procedure group runs its sentences in order. A halt bounds its group's acts, and a group's halts close it. Write a halt in one of four affirmative forms: the act to take in place of the excluded one, "Move a branch ref with `git reset --soft`." for one; a gate, "X only on Y."; an omission, "Keep X out of Y."; or a ground, "Treat X as no ground for Y." Give a group an `###` heading where a scanning reader needs to find it or other prose cites it by name. Keep a template the model emits in a fenced block, as an artifact to copy rather than document structure. Where prose would blur a line's precision, write that line in the language that states it exactly, a Lisp `cond` for a switch among cases for one, in a fenced block labeled with that language.

### The sentence

Write each line in the fewest words that keep its direction. Give each sentence one instruction. Where a sentence would carry two, split it. Write every directive as the act to take, turning the negation that would otherwise direct it, "never" or "do not" for one, into a halt form. Where the affirmative covers fewer cases than the negation it replaces, name an act for each case the negation covered. Where a contrast with what would otherwise happen helps the reader place the act, keep it beside the act. Write a fact about the rules, the reader, or the world as an instruction with a stance verb, hold, treat, read, count, or rely on. Write a vague qualifier, "short" or "where sure" for one, as a functional bound the reader can test on the artifact, in place of a static count. Close every out: a departure rests only on the user's licence or a fact a reader can check. Where a cut sentence described a failure mode, write the halt or arm that guards against it. Where a cut sentence carried a stance, write the instruction that enacts it. Keep a fact only where an instruction cannot run without it, a shell name or a config path for one.

### The register

Write every sentence blameless. Keep out of it any debt the reader or the user owes, and any guess at what the reader holds or where they have been. Keep the writer out of the reader's view: a plain imperative to the reader stays, and a sentence carrying the writer's attitude toward the reader goes. Let a person appear as a source or as someone the practice serves. Keep intensifiers out, "CRITICAL" for one. Write a header as a label. Leave room for trust: a rule is a prompt rather than source, so state the objective and the bounds and let the reader carry the act.

### The qualities

Let the opener name the whole scope, so every case a reader can find falls inside the rule. Let each machine line state a test a reader can run on the artifact, or a stance the reader holds. Define a term the file coins on its first use. Name a class by its mechanism and give it one example at most. Give each instruction one home. Keep every rule distinct and standing on its own text, with every other rule and rules file unnamed and unlinked. Group a rule's instructions into short paragraphs that each concern one thing.

### Routing

Route content before writing it. Where it is an always-on invariant, it goes to `rulesets/default/` and from there to every tier. Where it is an invariant for one kind of file, it goes to a path-scoped file under `rules/`. Where it differs for one model, it goes to that model's tier directory as an override of the same stem. Where it is a catalog, it goes to `references/`. Where it is enforcement, it goes to a hook. Where it is stance, it goes as an instruction into the rule whose object it concerns, and CLAUDE.md carries the user's greeting alone. Within a rule, where a sentence fixes a term, it goes to a definition group. Where a sentence directs an act, it goes to the decision or procedure group where it acts. Where a sentence is a halt, it closes the group it halts.

### Changing a rule

Hold every line of an existing rule as written against a failure seen in practice. Change a rule on the user's instruction or on cited evidence, a measured study or a primary text reached by URL for one. Change a rule by adding or sharpening a line, keeping the meaning of every directive the change touches. Make every change to a rules file, a ruleset body, or an agent file through an opus agent. Weigh a change by the outputs the rule steers. Leave the work a rule asks of an agent out of the weighing. Where two rules overlap, delegate `thinkies:survey-peers` on the overlapping lines to an opus agent, one overlap group per agent, one agent at a time. Then rewrite those lines into rules that each carry a distinct job, every directive's meaning kept. Where evidence points at removing a line, put the removal to the user as its own question, with its evidence.

Treat a line's apparent idleness as no ground for removing it. Remove a line only on the user's approval. Carry every line's full meaning through each rewording.

### Syncing the render

The renderer is `resolve.py render`, from the installed model-scoped-rulesets plugin. It runs in both directions between the bodies under `~/.claude/rulesets/$tier/` plus CLAUDE.md and `~/.claude/rulesets/renders/$tier/working-rules.md`, keyed on the rule markers, in the order of the `order:` list in `~/.claude/rulesets/manifest.yaml`. A render section runs from its marker to the next marker or the end of the file. The preamble, between the render's title and its first marker, is what CLAUDE.md holds, so CLAUDE.md goes unmarked. Hold a body under a tier directory other than `default/` as that tier's override of the stem. Hold every other stem of a tier as composed from `default/`. Edit whichever side is in hand, then run the renderer toward the other. Where the run refuses on an uncommitted target, restore that target with `git checkout HEAD -- <path>` and run again. After a reverse run, render every tier, then run `resolve.py check`. After a full-pass rewrite, read every removed line in the diff against HEAD and account for each before regenerating. Edit a rules file with one tool call per step, in place of a batch. When adding an always-on rule, add its stem to that order list in the same change. When renaming a rules file or a section another file cites, sweep the citations in the same change.
