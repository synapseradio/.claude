# Leave rulesets with plain rule files

At the end of this tutorial, your rules are plain Markdown files in a folder of your choosing,
and you hold a list of everything those files cannot carry. Leaving costs you nothing you wrote.
You ask Claude for the first step and run the uninstall yourself.

## Before you start

- A rulesets directory with at least one rule. The example uses the config from
  [Run one kind of agent on several models](run-agents-on-several-models.md).

## Write your rules out as plain files

1. Ask:

   ```text
   Eject my rules to plain files in ~/rules-plain.
   ```

   Claude writes one file for each rule every session and agent receives, here `voice.md`, and
   reports each file. Your rulesets directory stays as it is.

2. Read the list Claude reports beside the files. Plain files carry no conditions and no
   versions, so Claude names each one that stays behind, with its config line:

   | Stays behind | Why |
   | --- | --- |
   | the block `agent critic` | plain files reach everyone alike |
   | the block `agent critic and model haiku` | the same |
   | the version `brief` of `review-checklist` | a plain file holds one wording |

   Copy any rule from `~/.claude/rulesets/rules/` by hand where you want its text kept as well.

3. Uninstall the plugin:

   ```bash
   claude plugin uninstall rulesets@claude-root
   ```

   Nothing delivers the rulesets directory after that. It stays on disk, yours to keep or
   delete.

## What you have now

A folder of plain rule files to load however you like, such as from `~/.claude/rules`, which
Claude Code reads on its own.

## Related

- [Bring your existing rules in](bring-your-rules-in.md): the way back in.
- [Commands](commands.md): reference for the eject step Claude runs here.
