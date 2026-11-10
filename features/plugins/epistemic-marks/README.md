# epistemic-marks

This plugin stops Claude from ending a reply on a claim nobody has checked.

Claude marks each claim it has not verified with a short token at the end of the clause. Before the reply ends, the plugin finds every mark still standing and sends the reply back once. Claude then checks each claim and replaces its mark with a source, narrows the claim, or removes it.

> **Are you an AI agent installing this plugin?** Follow [SETUP.md](SETUP.md). It gives each command with its expected output, and the steps you must hand to a person.

## The marks

| Mark | Name | What it asks for |
| --- | --- | --- |
| `[?]` | the unsourced mark | a citation |
| `[.?]` | the secondhand mark | a check of what another agent or tool reported |
| `[^?]` | the caller's mark | a decision the agent that started this one can make |
| `[!?]` | the standing question | a decision only a person can make |

A mark inside a code block, or inside a longer code span, does not count. Neither does a mark in backticks on a line that names it, such as "the unsourced mark, `[?]`". Such a line describes the mark rather than claiming under it.

## Requirements

- Claude Code 2.1.268 or later.
- Python 3.9 or later. The hooks look for `python3`, then `python3.15` down to `python3.9`. If none of them on your `PATH` is 3.9 or later, set `EPISTEMIC_MARKS_PYTHON` to the interpreter's path.

Without a usable Python, each hook prints one line to stderr. Sessions then run with no rule text and no checks.

## Install

```sh
claude plugin marketplace add synapseradio/.claude
claude plugin install epistemic-marks@claude-root
```

Then run `/reload-plugins` in an open session, or restart Claude Code.

If the first command fails over SSH, run it again with `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` set.

## What it does

The plugin teaches the marks and enforces them, so it needs nothing else installed.

- **At every session and subagent start**, it adds the rule text from `rule-text/epistemic-marks.md` to the context. The rule text teaches Claude when to write each mark and how to resolve it.
- **When a reply ends**, the Stop hook blocks it once if it carries a mark. The block lists each marked line with what to do about it. A mark still standing after the rewrite is shown to you, and the reply ends.
- **When a subagent finishes**, the caller's mark and the standing question go back to the subagent. It puts them in its report, so the agent that started it can answer them or ask you.
- **After each batch of tool calls**, the PostToolBatch hook shows any marked line written since your last message. It never blocks, and it shows each line once per session.

## Turn it off

```sh
claude plugin disable epistemic-marks@claude-root
```

Then reload as after installing. `claude plugin enable epistemic-marks@claude-root` turns it back on, and `claude plugin uninstall epistemic-marks@claude-root` removes it.

## State and configuration

To show each PostToolBatch line only once, the plugin keeps a record of lines it has shown. The record holds a SHA-256 fingerprint of each line, never its text. Entries older than a day are removed.

Two environment variables configure the plugin:

- `EPISTEMIC_MARKS_PYTHON`: the Python that runs the hooks. It is tried before every other name.
- `VERIFY_MARKS_STATE_DIR`: where the record goes. Without it, the record goes to `verify-marks` under `CLAUDE_PLUGIN_DATA`, or else to `epistemic-marks-verify-marks` in the system temporary directory.

The plugin delivers its rule text as shipped, and no setting points it at another file. An update replaces `rule-text/epistemic-marks.md`, so local edits to it do not survive.

The plugin reads none of your configuration and no other plugin. The hooks that check replies read the session transcript whose path Claude Code passes them.

## More

[DESIGN.md](DESIGN.md) explains why the plugin works this way and how to test it.
