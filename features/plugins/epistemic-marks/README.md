# epistemic-marks

This plugin blocks a reply that still contains a claim that nobody has checked.

## What it is

An epistemic mark is a short token. A writer puts it at the end of a clause to show that the claim in that clause has no verified source yet. The plugin has two parts. Hooks check each reply for marks. Rule text teaches the model which marks to write.

A hook is a command that Claude Code runs when an event occurs. An event is a step in a session, such as the end of a reply. Rule text is a file that the plugin delivers into each session.

The plugin knows four marks. The label states the action that the mark needs.

| Mark | Name | Label |
| --- | --- | --- |
| `[?]` | the unsourced mark | `needs_citation` |
| `[.?]` | the secondhand mark | `needs_verification` |
| `[^?]` | the caller's mark | `escalate_decision` |
| `[!?]` | the standing question | `ask_user` |

A mark does not count in these places:

- a fenced code block
- an inline code span that holds more than the mark
- an inline code span that holds only the mark, on a line that also calls that mark by its name

A sentence that calls the mark by its name describes the mark. It makes no claim under the mark. A backticked mark on a line with no such name still counts. The hook lists each skipped mention, so no mention goes unseen.

The plugin ships both parts, so it needs no other plugin. It reads none of your configuration and none of your other plugins. The hooks that check replies read the session transcript. The transcript is the file that records the conversation. Claude Code gives its path in the hook input.

## Requirements

Make sure that you meet both requirements before you install the plugin.

1. Run `claude --version`.

   The output must read `2.1.268 (Claude Code)` or show a higher number. Claude Code 2.1.268 is the oldest version that anyone has verified. The plugin needs the `SubagentStart` event. If the number is lower, run `claude update`.

2. Run this command:

   ```sh
   python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'
   ```

   The exit code, the number that a command returns when it ends, must be 0. If it is not 0, install Python 3.9 or later. Then give the environment variable `EPISTEMIC_MARKS_PYTHON` the path of that Python. Do this in the place that starts Claude Code.

The hooks try `python3` first. Then they try `python3.15` down to `python3.9`. A name such as `python3.11` in your PATH can serve in place of `python3`. Your PATH holds the directories where your system looks for commands. If no usable Python exists, each hook prints one line to the error output. The session then has no rule text, and no hook checks a reply.

## Install

This repository is a marketplace, a catalog of plugins. Step 1 adds the catalog. Step 2 installs the plugin from the catalog.

1. Run this command:

   ```sh
   claude plugin marketplace add synapseradio/.claude
   ```

   The output ends with `Successfully added marketplace: claude-root (declared in user settings)`. If you run it again, the output says `already on disk`, and the exit code is 0.

   If the SSH connection to GitHub fails, run this command:

   ```sh
   CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1 claude plugin marketplace add synapseradio/.claude
   ```

2. Run this command:

   ```sh
   claude plugin install epistemic-marks@claude-root
   ```

   The output ends with `Successfully installed plugin: epistemic-marks@claude-root (scope: user)`. If you run it again, the output says `is already installed`, and the exit code is 0.

3. Person step: tell the person to run `/reload-plugins` in an open session, or to restart Claude Code.

   An agent cannot run a slash command, a command that starts with `/`, for the person.

## Check it loaded

Steps 1 to 5 are for the agent. Step 6 is for the person.

1. Run `claude plugin list`.

   The output has a section for `epistemic-marks@claude-root`. The section contains the line `Status: ✔ enabled`.

2. Run `claude plugin details epistemic-marks@claude-root`.

   The output contains `Hooks (5)  SessionStart, SubagentStart, PostToolBatch, Stop, SubagentStop`.

3. Run `claude plugin list --json`.

   The output is JSON, a structured text format. Read the value of `installPath`. If the output has a `readFromFolder` key, read that value instead. Call the path `PLUGIN_DIR`. Replace `PLUGIN_DIR` with the real path in steps 4 and 5.

4. Run this command:

   ```sh
   printf '%s' '{"hook_event_name":"SessionStart"}' | bash "PLUGIN_DIR/hooks/with-python.sh" "PLUGIN_DIR/hooks/deliver-rule.py"
   ```

   The output starts with this text:

   ```text
   {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<!-- rule: epistemic-marks -->
   ```

5. Run this command:

   ```sh
   printf '%s' '{"stop_hook_active":false,"last_assistant_message":"Nobody else calls it [?]."}' | bash "PLUGIN_DIR/hooks/with-python.sh" "PLUGIN_DIR/hooks/verify-marks.py"
   ```

   The output starts with `{"decision": "block"`. Now replace `[?]` in the command with the citation `(src/a.py:12)`. Run the command again. It prints nothing and exits with code 0.

6. Person step: after the reload, the person runs `/hooks` in the session.

   The output shows five entries. The agent tells the person which steps succeeded, and that step 6 is the person's step.

## Use

A hook acts only where a reply carries a mark. The plugin acts on three events.

The Stop hook checks a reply when the reply ends. If the reply carries a mark, the hook blocks the reply once. The reason for the block starts with `Your reply still carries unresolved marks`. It lists each marked line, with one instruction for each mark. If marks remain when the hook checks the reply again, the hook shows them to the user and does not block again.

A subagent is an agent that another agent starts. A subagent cannot reach the user. The SubagentStop hook lists the caller's mark and the standing question back to the subagent. The subagent puts them in its report. The report carries them to the caller. The caller is the agent that started the subagent.

The PostToolBatch hook checks the text that the model wrote since your last message. It does this after each group of tool calls, which are actions such as reading a file. It never blocks. It shows each line once for each session.

## Turn it off

1. Run `claude plugin disable epistemic-marks@claude-root`.

   The output ends with `Successfully disabled plugin: epistemic-marks (scope: user)`. The plugin then neither delivers rule text nor checks replies.

2. Person step: tell the person to run `/reload-plugins` or to restart Claude Code.

To turn the plugin on again, run `claude plugin enable epistemic-marks@claude-root`. A person must reload again. To remove the plugin, run `claude plugin uninstall epistemic-marks@claude-root`.

The setting `disableAllHooks` turns off the hooks of every plugin. It does not turn off this plugin alone.

## State and config

The PostToolBatch hook keeps a record of the lines that it has already shown. The record holds a SHA-256 fingerprint of each line. A fingerprint identifies a line and does not reveal its text. The record never holds the text of a line. The plugin removes entries that are older than one day.

The plugin writes the record to the first of these directories that applies:

1. The directory in `VERIFY_MARKS_STATE_DIR`.
2. The directory `verify-marks` inside the directory in `CLAUDE_PLUGIN_DATA`. Claude Code defines `CLAUDE_PLUGIN_DATA`.
3. The directory `epistemic-marks-verify-marks` inside the system temporary directory.

Two variables configure the plugin. Nothing else does.

- `EPISTEMIC_MARKS_PYTHON`: the name or path of the Python that runs the hooks. The launcher tries it before all other names.
- `VERIFY_MARKS_STATE_DIR`: the directory for the record. It overrides the other directories.

The plugin delivers the rule text file as shipped. No setting points delivery at another file. An update replaces `rule-text/epistemic-marks.md`, so an edit to that file does not survive an update.

## Test

Run this command in the plugin directory. In a clone of the repository, that directory is `features/plugins/epistemic-marks`.

```sh
python3 -m unittest discover -s tests -q
```

The output ends with `OK`. The tests need only the Python standard library, and they read nothing outside the plugin. One test compares the marks in the rule text with the marks in `epistemic_marks/marks.py`. It fails with the name of any mark that differs.

For the reasons behind the design, read [DESIGN.md](DESIGN.md).
