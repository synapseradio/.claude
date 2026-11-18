# Write your first rule

At the end of this tutorial, one instruction of yours sits in its own file, and every Claude Code
session and every agent a session starts receives it. A rule is one instruction kept as a Markdown
file. You ask Claude for each step, and Claude writes the files.

## Before you start

- The plugin installed and a first session behind you:
  [Installing rulesets](install.md).

## Add the rule and watch it arrive

1. In a Claude Code session, ask:

   ```text
   Add a rule named voice that says "Answer in plain words, point first."
   Give it to every session and agent.
   ```

   Claude writes the rule to `~/.claude/rulesets/rules/voice.md` and names it under `defaults`
   in `~/.claude/rulesets/config.yaml`, the list every session and agent receives. It reports
   both files and who gains the rule.

2. Start a new session with `claude`, since a session receives its rules when it starts. Then ask:

   ```text
   What rules did this session receive?
   ```

   Claude reads the plugin's record of the session and reports one delivery, the plugin's word
   for one session or agent receiving its rules, carrying the one rule `voice`. The session also
   opened on a message such as
   ``no declared model name claims `claude-opus-4-8` ``, because the config names no model yet.

3. Ask Claude to name the models you use, by family:

   ```text
   Declare the models haiku, sonnet and opus in my rulesets config.
   ```

   Claude writes the names into the config, which now holds these lines:

   ```yaml
   models: haiku sonnet opus
   defaults: voice
   ```

   A declared name covers every model whose identifier starts with `claude-` and that name, so
   sessions on those models now start without the message.

## What you have now

Your rulesets directory holds one file per instruction and one config that says who receives
which. To improve the rule, ask Claude to change its text: the one file changes, and your next
session and every agent started from then on receive the new wording. The other tutorials start
from this directory and its config.

## Related

- [Send a rule to one agent](send-a-rule-to-one-agent.md): give one kind of agent an instruction
  of its own.
- [Check your rules before they are delivered](check-your-rules.md): have Claude find every
  mistake in one pass.
- [The rulesets directory and config](config.md): reference for every key and form the config
  takes.
