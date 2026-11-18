# Keep a rule away from one model

At the end of this tutorial, a rule reaches every session and agent except those running on haiku,
and Claude can name the config line that holds it back. Use this for an instruction that helps
most models and misleads one. You ask Claude for each step.

## Before you start

- The rule `voice` and the config from [Write your first rule](write-your-first-rule.md), with
  `haiku` among its declared models.

## Hold the rule back from haiku

1. Ask for a rule that everyone receives:

   ```text
   Add a rule named code-style that says "Name every function for what it returns."
   Give it to every session and agent.
   ```

   Claude writes `rules/code-style.md` and adds the name to `defaults`. It reports that every
   session and agent gains the rule.

2. Ask Claude to hold it back:

   ```text
   Keep code-style away from haiku.
   ```

   Claude adds a block with an `exclude`, and the config now holds:

   ```yaml
   models: haiku sonnet opus
   defaults: voice code-style
   model haiku:
     exclude: code-style
   ```

   Claude reports who loses the rule:

   | Who | Receives |
   | --- | --- |
   | a session or agent on haiku | `voice` |
   | a session or agent on any other model | `voice`, `code-style` |

3. Ask why:

   ```text
   Why does a haiku agent miss code-style?
   ```

   Claude names the winning line, `config.yaml:4` in the config above, `exclude code-style` under
   `model haiku`, and the line it beat, `defaults` on line 2.

A block for one agent outranks a block for one model. If an agent on haiku still receives the
rule, ask "why did that agent get code-style?" and Claude names the line that won and moves the
exclude above it on your word.

## What you have now

One model works without an instruction that every other model keeps, and the rule still lives in
one file.

## Related

- [Send a rule to one agent](send-a-rule-to-one-agent.md): the opposite move, an extra rule for
  one kind of agent.
- [Run one kind of agent on several models](run-agents-on-several-models.md): give each model its
  own wording of a rule.
- [The rulesets directory and config](config.md): reference for `exclude` and which statement
  wins.
