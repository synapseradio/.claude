# Delivery

## What it delivers, and to whom

| Context | When it receives rules | Hook |
| --- | --- | --- |
| The main session | at start, resume, clear, and compaction | `SessionStart` |
| A delegate | when it starts | `SubagentStart` |
| The main session, after a model switch | when the switch composes different rules | `PostModelSwitch` |

Each delivery carries the whole composition for that context, never a difference. The rules arrive
in name order. Before each rule's body, delivery writes the line `<!-- rule: <name> -->` and a blank
line, so a rule file carries no marker line of its own. A rule at a variant arrives under the same
marker, with the variant's text and the variant left unnamed. The same composition always yields the
same bytes.

A delivery splits into parts. One hook entry carries one part, and a part holds whole rule bodies up
to 9,000 characters, counting each rule's marker and blank line. A rule never splits across parts.
A delivery carries at most 10 parts; a rule that would need an eleventh part is left out, and
`check` warns about the context. A rule whose body and marker pass 9,000 characters on their own is
a `check` error, and delivery withholds it.

A delegate composes from its own facts: its model, its agent type, and the flags that hold. The
delegate's model comes from the first of these that names one: the model the caller named for the
spawn, the agent definition's pin, the `CLAUDE_CODE_SUBAGENT_MODEL` variable, and the parent
session's recorded model. A haiku delegate under an opus session receives the haiku composition when
the spawn names haiku, and the session keeps the opus one.

Several delegates of one agent type spawned in one message can each name a different model. The
harness tells a starting delegate nothing that identifies its spawn, so each delegate takes the
oldest spawn of its type in that message that no earlier delegate took, and keeps it when resumed.
The harness does not promise that delegates start in the order they were spawned; a delegate that
starts out of order takes another delegate's model, and no notice reports the swap. A delegate that
finds every such spawn taken takes the model they all name, or, where they name different models,
the next source above, with a notice of ambiguity in its delivery record.

After a model switch, the plugin composes again for the new model. Where the new model composes the
same rules at the same variants as the rules last delivered, it delivers nothing. Where it composes
different rules, it delivers them, and the earlier rules remain in the conversation above them; the
plugin cannot retract text it already delivered.

Three further hooks deliver nothing. A `PreToolUse` hook on the `Agent` tool records each spawn and
the model its caller names, if any. An `InstructionsLoaded` hook records each instruction file the harness
loaded. A `SessionEnd` hook ends the session's toggles. The records feed the checks below.

A delivery can skip a reference, withhold a rule, leave a rule out, or reach no rule, and each
draws a notice. At session start, the plugin shows the notices to you as a message and never puts
them into the agent's context. A delegate's start and a model switch show no message; their
notices sit in the delivery record, under `notices`. A session start that raises nothing shows no
message.

## What it leaves alone

- **Forks.** A forked session and a fork subagent already carry the parent's rules in the
  conversation they inherit, so the plugin gives them nothing, records nothing for them, and shows
  no notice.
- **The harness's own rules.** A project's `.claude/rules` folder and `~/.claude/rules` load as they
  would without the plugin. A rule kept both there and in the pool reaches a context twice, so move
  it into the pool and run `load-check` to confirm nothing still auto-loads it.
- **Agent definitions and spawn prompts.** Delivery reads an agent definition for its model pin and
  its tools, and writes into neither the definition nor the prompt.
- **Text already delivered.** No toggle and no model switch retracts a rule already in a context.
- **A session that cannot start the engine.** Where no interpreter reports Python 3.14 with PyYAML,
  the session starts without the plugin's rules and you see a message naming the requirement.

Where the manifest is missing or does not parse, delivery sends the default form of every rule in
the pool, with a notice. Where no rulesets directory exists, the first delivery creates an empty one
and says where, at session start.
