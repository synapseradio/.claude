# Switch rules for the agents you start next

At the end of this tutorial, the agents your session starts next receive a different set of rules,
and your conversation has carried on without a restart. The plugin calls these agents delegates,
and the switch a toggle. You ask Claude for each step.

## Before you start

- The flag `terse` and the version `voice@terse` from
  [Try two versions of a rule](try-two-versions-of-a-rule.md).
- A session started with plain `claude`.

## Turn a flag on, then off again

1. Ask:

   ```text
   Turn on terse for my delegates.
   ```

   Claude answers in one sentence: delegates started from now on hold the flag `terse`.

2. Have Claude start an agent on any small task, then ask:

   ```text
   What did that agent receive?
   ```

   Claude reports the agent's delivery with the flag `terse` and the rule `voice` at its `terse`
   version. Your own session keeps the rules it started with, and so does any agent that was
   already running.

3. Undo it:

   ```text
   Clear my toggles.
   ```

   Claude answers that delegates started from now on receive what the config and the launch flags
   give them.

## Other toggles to ask for

| You want the next agents to | Ask Claude, for example |
| --- | --- |
| receive every rule you have | "give my delegates every rule" |
| receive no rule | "give my delegates no rules" |
| drop one flag | "stop giving delegates terse" |

A toggle lasts until you clear it, clear or resume the conversation, or close the session, and it
survives compaction. A flag name the config does not declare changes nothing, and Claude reports
the name.

## What you have now

A way to try a change on the next task while the conversation keeps its own rules.

## Related

- [Try two versions of a rule](try-two-versions-of-a-rule.md): compare two whole sessions, one
  under each wording.
- [Delivery](delivery.md): reference for when each session and agent receives rules.
- [Commands](commands.md): reference for each toggle action.
