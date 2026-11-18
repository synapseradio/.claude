# Installing rulesets

This how-to takes you from a machine without the plugin to a Claude Code session that runs it, with
an empty rulesets directory at `~/.claude/rulesets` ready for your first rule. The commands on this
page are the only ones you type. From the first session on, you ask Claude in words and Claude does
the work.

## Before you start

- Claude Code, with its `claude` command on your path.
- Python 3.15 or later with PyYAML. Check the interpreter, then install PyYAML for it:

  ```bash
  python3.15 --version
  python3.15 -m pip install pyyaml
  ```

The plugin tries `python3.15`, then `python3`, and runs the first that reports 3.15 or later and
imports `yaml`. To name another interpreter, set `RULESETS_PYTHON` to its path or name.

## Install the plugin and start a session

1. Add the marketplace that holds the plugin. Its name is `claude-root`.

   ```bash
   claude plugin marketplace add synapseradio/.claude
   ```

2. Install the plugin from it.

   ```bash
   claude plugin install rulesets@claude-root
   ```

3. Start a session.

   ```bash
   claude
   ```

   The session opens with a message from the plugin, three lines long:

   ```text
   no rulesets directory existed; an empty one was scaffolded at `~/.claude/rulesets`
   no declared model name claims `claude-opus-4-8`
   the context received nothing: no rule reaches it
   ```

   The path and the model are yours. The first line says the plugin created your rulesets
   directory, with an empty `rules/` folder and a `config.yaml` that declares nothing. The other
   two lines describe that empty state, and
   [Write your first rule](write-your-first-rule.md) clears both.

To install from a local checkout, give step 1 the directory that holds
`.claude-plugin/marketplace.json` in place of `synapseradio/.claude`.

## Confirm it worked

Ask Claude:

```text
Check my rulesets directory.
```

Claude runs the plugin's check and reports that the directory has no errors and no warnings. The
plugin is installed, and the directory is ready.

## If something goes wrong

| You see | Cause | Do |
| --- | --- | --- |
| a message at session start naming Python 3.15 and PyYAML, and no rules | no interpreter on your path runs the plugin | install PyYAML for Python 3.15 or later, or set `RULESETS_PYTHON` |
| no message in the first session, and no `~/.claude/rulesets` | the plugin is not installed or not enabled | confirm the plugin is installed and enabled, then start a new session |
| a message naming `config.yaml` in a directory that holds an older config file | the plugin reads `config.yaml` and no other config file | ask Claude "move my old rulesets config into config.yaml" |
| each instruction arriving twice | your own settings file runs hooks that deliver rules on the same events | remove your entries for those hooks |

The plugin registers hooks on `SessionStart`, `SubagentStart`, `PostModelSwitch`, `PreToolUse` for
the `Agent` tool, `InstructionsLoaded`, and `SessionEnd`.

Where `CLAUDE_CONFIG_DIR` is set, the rulesets directory is `rulesets/` under that path.

## Uninstall the plugin

```bash
claude plugin uninstall rulesets@claude-root
```

The rulesets directory is yours and stays where it is; nothing delivers it after that.
[Leave rulesets with plain rule files](leave-rulesets.md) turns your rules back into plain files
first.

## Related

- [Write your first rule](write-your-first-rule.md): the next step, one instruction that every
  session and agent receives.
- [Bring your existing rules in](bring-your-rules-in.md): start from a rules folder you already
  have.
- [Delivery](delivery.md): reference for which sessions and agents receive rules, and when.
