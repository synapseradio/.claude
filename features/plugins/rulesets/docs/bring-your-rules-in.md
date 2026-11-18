# Bring your existing rules in

At the end of this tutorial, the plugin delivers the rules you already keep in a folder, Claude
has shown that every session and agent receives the same text as before, and no rule arrives
twice. Your folder stays as it was until you say otherwise. You ask Claude for each step.

The example brings in `~/.claude/rules`, the folder Claude Code loads on its own.

## Before you start

- The plugin installed and a first session behind you:
  [Installing rulesets](install.md).
- A folder of rule files, one Markdown file per rule.

## Move a rules folder into rulesets

1. Ask:

   ```text
   Bring my rules in from ~/.claude/rules, and declare the models haiku, sonnet and opus.
   ```

   Claude builds a new rulesets directory beside your folder, one rule per file, with a config
   that gives every rule to every session and agent:

   ```yaml
   models: haiku sonnet opus
   defaults: all.*
   ```

   It then compares what your folder delivers with what the new directory delivers, and reports
   how many kinds of session and agent it compared and each one that differs. With a plain
   folder, none differs.

2. Answer Claude's question about putting the new directory in place. Your first session
   created an empty `~/.claude/rulesets`, so Claude asks before it sets that one aside under a
   new name and moves the new directory in.

3. Answer Claude's question about the old copies. Claude Code still loads `~/.claude/rules` on
   its own, so each rule would arrive twice. Claude asks before it deletes each old copy. A file
   whose own header limits it to certain file paths stays where it is, and Claude says why.

4. Start a new session with `claude`, then ask:

   ```text
   Is any of my rules still loading from my old rules folder?
   ```

   Claude checks what Claude Code loaded in this session and reports that no rule of yours
   loaded from the old folder. A rule it does name still has a copy there to remove.

## What you have now

The same instructions as before, now one config away from being aimed by agent, model or flag.

## Related

- [Send a rule to one agent](send-a-rule-to-one-agent.md): start aiming the rules you brought
  in.
- [Leave rulesets with plain rule files](leave-rulesets.md): the way back out.
- [Commands](commands.md): reference for the adopt and compare steps Claude runs here.
