---
paths:
  - "**/rules/*.md"
  - "**/CLAUDE.md"
---

<rule name="writing-rules">

## writing-rules

When you are writing or changing a rules file, or CLAUDE.md, optimize for a rules file whose reader decides the same way every turn and still knows what the decision serves where the machine runs out.

A rule gets read every turn, and each sentence in it positions the reader. The reasons in the why let the reader extend the rule to a case the machine never named. A warrant inside a machine line makes the reader parse the why to find the what, so the why carries every warrant and each machine line goes bare. A rule that argues for its own existence spends valuable attention on a decision the user already took. A rule reads as binding at its plain statement. An intensifier in front of it adds emphasis and no force. The frontmatter loads a path-scoped file and the trigger tells the reader why it fired. An example stands where a mechanism is missing, and a list of examples teaches the list.

### The form

A rules file is markdown, and it opens on its marker, `<!-- rule: stem -->` alone on its line at column 0, where the stem is the filename without .md. One blank line follows the marker, then the title, `## stem`. A path-scoped rule keeps `paths:` frontmatter above the marker, with globs that match file paths, and still names the activity in its trigger. Below the title the trigger and the target come first, then the why, then the machine.

The trigger and the target open the body as one sentence: the situation that fires the rule, or the scope of a rule that always holds, then "optimize for" and a phrase naming one quality in one clause. Every other quality the rule serves goes to the why. The why is the paragraph after that one, and it holds the reasons: the statement of why the practice matters in the rule's own matter, then the mechanisms and costs, then any grounding with its citation.

The machine is a sequence of groups, each a paragraph or a `###` section. A definition group fixes terms, one per sentence. A decision group is ordered, its sentences arms with the first that fits winning, written "Where X, Y." or "When X, Y." with "Otherwise, Z." last, as bullets where the arms are many. A procedure group runs its sentences in order. A halt reads "Never X." or "X only on Y.", and a group's halts close it. A group gets an `###` heading where a scanning reader needs to find it, or where other prose cites it by name. A template the model emits stays in a fenced block, so it reads as an artifact to copy and never as document structure.

### The register

The why is remembered for its statement of why the practice matters, so no frame stands in front of it and each why opens on its own subject, with no phrasing repeated across rules. The writer stays out of the reader's view, so a plain imperative that addresses the reader stays, and a sentence carrying the writer's attitude toward the reader goes. Every sentence is blameless, names no debt to the reader or the user, and assumes nothing about what the reader holds or where they have been. A tendency reads as a tendency. A cost reads as a cost. A person appears as a source or as someone the practice serves. An intensifier, "CRITICAL" for one, appears in no rule. A header in a rules file is a label. Attention is the currency, and the word for it is valuable attention.

### The qualities

The trigger names what fires the rule now. The machine states what the rule requires, and each machine line states a test a reader can run on the artifact. A term the file coins gets its definition on its first use, and the definition carries a meaning and no warrant. A class is named by its mechanism and carries one example at most. Where a topic appears in another file, the rule restates the one clause it rests on and keeps the full statement in one place, with no link between rules files. Where a neighbor continues the territory, the rule names it, and otherwise the trigger alone bounds the rule. The why carries every warrant, and a machine line carries none.

### Routing

Route content before writing it. Where the content is an invariant, it goes to `rules/`. Where it is a catalog, it goes to `references/`. Where it is enforcement, it goes to a hook. Where it is stance, it goes to CLAUDE.md. Within a rule, where a sentence fixes a term, it goes to a definition group. Where a sentence directs an act, it goes to the decision or procedure group where it acts. Where a sentence is a halt, it closes the group it halts. A subsection gets its own trigger only where it fires on less than the file does.

### Syncing the render

The renderer at `scripts/agent-configs/render-working-rules.py` runs in both directions between the bodies under `~/.claude/rulesets/$model/` plus CLAUDE.md and `~/.claude/references/$model/working-rules.md`, keyed on the rule markers, in the order the `WORKING_RULES_ORDER` tuple in `scripts/agent-configs/projection.py` names. A section of the render runs from its marker to the next one or to the end of the file, and the preamble is what sits between the render's title and its first marker, which is what CLAUDE.md holds, so CLAUDE.md carries no marker. It renders every model forward with no argument, scopes a forward run to one model with `--model`, and splits the `default` model's render back with `--reverse`. Edit whichever side is in hand, then run the renderer toward the other, so the two never disagree. When adding an always-on rule, add its stem to that tuple in the same change. When renaming a rules file or a section another file cites, sweep the citations in the same change.

Never argue for the rule inside it. Never give a class more than one example.

</rule>
