# Measure what your rules cost

At the end of this tutorial, you have a figure for the tokens each session and agent carries in
rules, and the change one edit made to each figure. Rules sit in a context from its first
message, so the figure tells you what an instruction costs before you keep it. You ask Claude for
each step.

## Before you start

- The rule `review-checklist` for the `critic` agent, from
  [Send a rule to one agent](send-a-rule-to-one-agent.md).

## Weigh an edit before you keep it

1. Ask for the figures as they stand:

   ```text
   How many tokens does each agent carry in rules?
   ```

   Claude reports a line for each kind of session and agent your config tells apart, with its
   characters, words and estimated tokens. With the two example rules, the main session carries
   about 21 tokens and a critic about 56.

2. Ask for an edit:

   ```text
   Add "Give one example for each claim." to the end of the voice rule.
   ```

   Claude edits `rules/voice.md` and reports the file.

3. Ask for the comparison:

   ```text
   How many tokens does each agent carry now, compared with before?
   ```

   Claude reports each figure beside the one from before the edit, with the change:

   | Who | Before | Now | Change |
   | --- | ---: | ---: | ---: |
   | the main session | 21 | 33 | +12 |
   | a critic | 56 | 68 | +12 |

   The figures are estimates for English prose. Ask in the session that made the edit, since
   Claude takes the "before" from the snapshot it made there.

## What you have now

A number to hold each rule edit against, for every agent it reaches.

## Related

- [Load long guidance on demand](load-long-guidance-on-demand.md): move a long rule's body out
  of every context.
- [Run one kind of agent on several models](run-agents-on-several-models.md): give a small model
  a shorter wording.
- [Commands](commands.md): reference for how the estimate is computed.
