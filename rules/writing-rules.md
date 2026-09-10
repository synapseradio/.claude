---
paths:
  - "**/rules/*.md"
  - "**/rulesets/*/*.md"
  - "**/rulesets/renders/*/working-rules.md"
  - "**/CLAUDE.md"
---

<!-- rule: writing-rules -->

## writing-rules

For every rules file, every body under a rulesets tier, every working-rules render, and every CLAUDE.md you write or change, optimize for a rules file whose reader decides the same way every turn and holds every line as binding.

### The form

A rules file is markdown, and it opens on its marker, `<!-- rule: stem -->` alone on its line at column 0, where the stem is the filename without .md. One blank line follows the marker, then the title, `## stem`. A path-scoped rule keeps `paths:` frontmatter above the marker, with globs that match file paths. Below the title comes the opener, then the machine, and nothing else.

The opener is one sentence. It names the rule's whole scope as a universal, "For every X" or "In every context and every turn", then says "optimize for" and names one quality in one clause. Never open a rule on a condition, "When you are X" or "This rule applies when" for one. Never write a paragraph that argues for the rule.

The machine is a sequence of groups, each a paragraph or a `###` section. A definition group fixes terms, one per sentence, each carrying a meaning and no warrant. A decision group is ordered, its sentences arms with the first that fits winning, written "Where X, Y." or "When X, Y." with "Otherwise, Z." last, as bullets where the arms are many. A procedure group runs its sentences in order. A halt reads "Never X." or "X only on Y.", and a group's halts close it. Give a group an `###` heading where a scanning reader needs to find it, or where other prose cites it by name. Keep a template the model emits in a fenced block, so it reads as an artifact to copy and never as document structure.

### The sentence

Give each sentence one instruction. Where a sentence would carry two, split it. Write a fact about the rules, the reader, or the world as an instruction with a stance verb, hold, treat, read, count, or rely on, so it reads as binding and not as commentary. Write a vague qualifier, "short" or "where sure" for one, as a functional bound the reader can test on the artifact, never as a static count. Close every out: a departure rests on the user's licence or on a fact a reader can check, and on nothing the reader alone judges. Where a cut sentence described a failure mode, write the halt or the arm that guards against it. Where a cut sentence carried a stance, write the instruction that enacts it. Keep a fact only where an instruction cannot run without it, a shell name or a config path for one.

### The register

Write every sentence blameless, naming no debt to the reader or the user and assuming nothing about what the reader holds or where they have been. Keep the writer out of the reader's view: a plain imperative that addresses the reader stays, and a sentence carrying the writer's attitude toward the reader goes. Let a person appear as a source or as someone the practice serves. Write no intensifier, "CRITICAL" for one. Write a header as a label. Leave room for trust: a rule is a prompt and not source, so state the objective and the bounds and let the reader carry the act.

### The qualities

Let the opener name the whole scope, so no reader can find a case the rule leaves open. Let each machine line state a test a reader can run on the artifact, or a stance the reader holds. Define a term the file coins on its first use. Name a class by its mechanism and give it one example at most. Give each instruction one home, and let another rule point to it by the rule's name, "under the rule on prose" for one, with no link between rules files. Where a neighbor continues the territory, name it in the opener.

### Routing

Route content before writing it. Where the content is an always-on invariant, it goes to `rulesets/default/` and from there to every tier. Where it is an invariant for one kind of file, it goes to a path-scoped file under `rules/`. Where it differs for one model, it goes to that model's tier directory as an override of the same stem. Where it is a catalog, it goes to `references/`. Where it is enforcement, it goes to a hook. Where it is stance, it goes as an instruction into the rule whose object it concerns, and CLAUDE.md carries the user's greeting and precedence alone. Within a rule, where a sentence fixes a term, it goes to a definition group. Where a sentence directs an act, it goes to the decision or procedure group where it acts. Where a sentence is a halt, it closes the group it halts.

### Syncing the render

The renderer is `resolve.py render`, from the installed model-scoped-rulesets plugin. It runs in both directions between the bodies under `~/.claude/rulesets/$tier/` plus CLAUDE.md and `~/.claude/rulesets/renders/$tier/working-rules.md`, keyed on the rule markers, in the order the `order:` list in `~/.claude/rulesets/manifest.yaml` names. A section of the render runs from its marker to the next one or to the end of the file. The preamble is what sits between the render's title and its first marker, which is what CLAUDE.md holds, so CLAUDE.md carries no marker. Hold a body under a tier directory other than `default/` as that tier's override of the stem. Hold every other stem of a tier as composed from `default/`. Edit whichever side is in hand, then run the renderer toward the other, so the two never disagree. Where the run refuses on an uncommitted target, restore that target with `git checkout HEAD -- <path>` and run again. After a reverse run, render every tier, then run `resolve.py check`. After a full-pass rewrite, read every removed line in the diff against HEAD and account for each before regenerating. Edit a rules file with one tool call per step, never a batch. When adding an always-on rule, add its stem to that order list in the same change. When renaming a rules file or a section another file cites, sweep the citations in the same change.

Never argue for the rule inside it. Never open a rule on a condition. Never join two instructions in one sentence. Never give a class more than one example. Never write an intensifier.
