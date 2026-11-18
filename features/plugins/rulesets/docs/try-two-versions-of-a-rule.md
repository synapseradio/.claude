# Try two versions of a rule

At the end of this tutorial, two sessions have run the same task, one under each wording of a
rule, and Claude has shown that the wording is the only thing that differed between them. You ask
Claude for each step and start the two sessions yourself.

## Before you start

- The rule `voice` and the config from [Write your first rule](write-your-first-rule.md).

## Run one task under each wording

1. Ask for the second wording and a switch for it:

   ```text
   Add a version of the voice rule named terse that says "Answer in one sentence."
   Add a flag named terse that switches to it.
   ```

   Claude writes the new wording beside the rule, with the version's name after an `@`:

   ```text
   rules/
     voice.md         Answer in plain words, point first.
     voice@terse.md   Answer in one sentence.
   ```

   It also declares a flag, a name you switch on when you start Claude Code, and lets the flag
   pick the version. The config now holds:

   ```yaml
   models: haiku sonnet opus
   flags: terse
   defaults: voice
   flag terse:
     include: voice@terse
   ```

2. Start two sessions, one each way, and give both the same task:

   | Start Claude Code with | Every session and agent receives |
   | --- | --- |
   | `claude` | `voice` |
   | `RULESETS_FLAGS=terse claude` | `voice@terse` |

   The flagged session and its agents work under "Answer in one sentence." A flag the config
   does not declare is dropped, and the session opens on a message naming it, so a typing mistake
   shows at once.

3. In each session, ask:

   ```text
   What did this session receive? Include its identifier.
   ```

   Claude reports the session's identifier, its flags, and the version of `voice` it received:
   `terse` in the flagged session, the default in the other.

4. In either session, ask, with the two identifiers in place:

   ```text
   Compare what sessions <first identifier> and <second identifier> received.
   ```

   Claude reports each session's flags and one line of difference: `voice`, at `default` in one
   session and `terse` in the other.

## What you have now

Two runs of one task, each tied by its record to the wording it ran under. To keep the terse
wording for good, ask Claude to make it the rule's text; to drop it, ask Claude to remove the
version and the flag.

## Related

- [Switch rules for the agents you start next](switch-rules-mid-session.md): turn the same flag
  on inside a running session.
- [See what an agent received, and why](see-what-an-agent-received.md): read one session's record
  in full.
- [Where records live](records.md): reference for the files that hold each session's record.
