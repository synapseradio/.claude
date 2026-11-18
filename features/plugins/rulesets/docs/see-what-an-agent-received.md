# See what an agent received, and why

At the end of this tutorial, you know which rules your session and one of its agents received,
which config line decided one of them, and whether the session got what your config says it
should. You ask Claude for each step.

When an agent behaves in a way you did not expect, these asks tell you whether its instructions
were the cause.

## Before you start

- The rule `review-checklist` for the `critic` agent, from
  [Send a rule to one agent](send-a-rule-to-one-agent.md).
- A session in which Claude has started a critic.

## Read the record, then ask why

1. Ask what arrived:

   ```text
   What did this session and its agents receive?
   ```

   The plugin records every delivery. Claude reports one line for each: who received it, the
   session or an agent, the model it ran on and where the plugin learned that model, the number
   of rules, and any flags. Here that is the session with one rule and the critic with two.

2. Ask for the rules by name:

   ```text
   Which rules did the critic receive?
   ```

   Claude lists `review-checklist` and `voice`, each with its version where it has one, and
   anything the delivery held back, with the reason.

3. Ask why one of them arrived:

   ```text
   Why did critic get review-checklist?
   ```

   Claude names the line that decided it: `config.yaml:4` in the config from
   [Send a rule to one agent](send-a-rule-to-one-agent.md), under the condition `agent critic`,
   with the reference `include review-checklist`. Where other lines touched the rule, Claude
   lists each line the winner beat.

4. Ask whether the record matches your config:

   ```text
   Did this session receive what my rules say?
   ```

   Claude composes the rules again from your config as it stands and compares them with the
   record. With no edit since the session started, it reports no difference. A difference names
   the rule, and means your rules or config changed after the delivery or a delivery went wrong.

## What you have now

A record to check an agent's instructions against, and a line number for every rule in it.

## Related

- [Check your rules before they are delivered](check-your-rules.md): find mistakes before any
  session starts.
- [Where records live](records.md): reference for the files that hold the record.
- [Commands](commands.md): reference for what Claude runs to answer each ask.
