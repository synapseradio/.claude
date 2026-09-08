---
paths:
  - "**/rules/*.md"
  - "**/CLAUDE.md"
---

<rule name="writing-rules">

  <applies_when>
    You are writing or changing a rules file, or CLAUDE.md.
  </applies_when>

  <optimize_for>
    a rules file whose reader decides the same way every turn and still knows what the decision serves where the machine runs out.
    <why_it_matters>
      A rule gets read every turn, and each sentence in it positions the reader. The reasons in the why let the reader extend the rule to a case the machine never named. A warrant inside a machine line makes the reader parse the why to find the what, so the why carries every warrant and each machine line goes bare. A rule that argues for its own existence spends valuable attention on a decision the user already took. The frontmatter loads a path-scoped file and the trigger tells the reader why it fired. An example stands where a mechanism is missing, and a list of examples teaches the list.
    </why_it_matters>
  </optimize_for>

  <define name="form">
    A rules file carries one rule element, `<rule name="stem">` through `</rule>`, where the stem is the filename without .md. A path-scoped rule keeps `paths:` frontmatter above the element, with globs that match file paths, and still names the activity in its trigger. Inside the element, the trigger comes first, then the target with its why, then the machine.

    The trigger, `<applies_when>`, is a complete sentence stating the situation that fires the rule, or the scope of a rule that always holds. The target, `<optimize_for>`, is a phrase that reads after the words "Optimize for", lowercase and ending in a period, on its own line. It names one quality in one clause, and every other quality the rule serves goes to the why. The why, `<why_it_matters>`, nests last inside the target and holds the reasons: the statement of why the practice matters in the rule's own matter, then the mechanisms and costs, then any grounding with its citation.

    The machine is a sequence of groups. A `<define>` fixes terms, one per sentence. A `<decide>` is an ordered decision whose sentences are arms, the first that fits winning, written "Where X, Y." or "When X, Y." with "Otherwise, Z." last, as bullets where the arms are many. A `<do>` is a procedure whose sentences run in order. A `<require>` holds halts, "Never X." or "X only on Y." A concept tag such as `<concern>` names a section other prose cites, with mode tags nested where a group has one mode. The `name` attribute appears where a rule has several groups of one mode or where prose cites the group by name, as plain words with spaces. A template the model emits stays in a fenced block, so it reads as an artifact to copy and never as document structure.
  </define>

  <define name="register">
    The why is remembered for its statement of why the practice matters, so no frame stands in front of it and each why opens on its own subject, with no phrasing repeated across rules. The writer stays out of the reader's view: a plain imperative that addresses the reader stays, and a sentence carrying the writer's attitude toward the reader goes. Every sentence is blameless, names no debt to the reader or the user, and assumes nothing about what the reader holds or where they have been. A tendency reads as a tendency. A cost reads as a cost. A person appears as a source or as someone the practice serves. Attention is the currency, and the word for it is valuable attention.
  </define>

  <define name="qualities">
    The trigger names what fires the rule now. The machine states what the rule requires, and each machine line states a test a reader can run on the artifact. A term the file coins gets its definition on its first use, and the definition carries a meaning and no warrant. A class is named by its mechanism and carries one example at most. Where a topic appears in another file, the rule restates the one clause it rests on and keeps the full statement in one place, with no link between rules files. Where a neighbor continues the territory, the rule names it, and otherwise the trigger alone bounds the rule. The why carries every warrant, and a machine line carries none.
  </define>

  <decide name="route">
    Route content before writing it. Where the content is an invariant, it goes to `rules/`. Where it is a catalog, it goes to `references/`. Where it is enforcement, it goes to a hook. Where it is stance, it goes to CLAUDE.md. Within a rule, where a sentence fixes a term, it goes to a define group. Where a sentence directs an act, it goes to the decide or do group where it acts. Where a sentence is a halt, it goes to the require group. A subsection gets its own trigger only where it fires on less than the file does.
  </decide>

  <require>
    Never argue for the rule inside it. Never give a class more than one example.
  </require>

  <do name="sync">
    The generator at `scripts/sync-agent-configs.py` runs in both directions between the rules files plus CLAUDE.md and `~/.claude/references/working-rules.md`, keyed on the rule elements and the preamble tags, in the order its `WORKING_RULES_ORDER` tuple names. Edit whichever side is in hand, then run the generator toward the other, so the two never disagree. When adding an always-on rule, add its stem to that tuple in the same change. When renaming a rules file or a section another file cites, sweep the citations in the same change.
  </do>

</rule>
