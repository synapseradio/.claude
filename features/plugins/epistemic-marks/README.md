# epistemic-marks

epistemic-marks stops Claude Code from ending a reply on a claim nobody has checked.

The plugin adds rule text, a section of instructions, to every session. It teaches Claude to end each unverified clause with a mark, a short token such as `[?]`. When a reply ends with a mark still in it, a hook sends the reply back once. Claude then replaces each mark with a source, narrows the claim to what the source backs, or removes the claim.

> **An AI agent installing this plugin for someone?** Follow [SETUP.md](SETUP.md). It gives each command with its expected output, and names the steps to hand to the person.

## Marks

| Mark | Name | Resolved by |
| --- | --- | --- |
| `[?]` | the unsourced mark | finding a source for the claim |
| `[.?]` | the secondhand mark | checking what another agent, a tool, or a person reported |
| `[^?]` | the caller's mark | a decision from the agent that started this one |
| `[!?]` | the standing question | a decision only a person can make |

A mark inside a fenced code block, or inside a longer code span, does not count. Nor does a mark alone in a code span on a line that names it, as in "the unsourced mark, `[?]`". That line talks about the mark rather than claiming under it.

## Requirements

The plugin runs on Claude Code 2.1.268 or later, the oldest version tested, and on Python 3.9 or later.

The hooks look for Python under `python3`, then `python3.15` down to `python3.9`, and use the first that is 3.9 or later. If none is, set `EPISTEMIC_MARKS_PYTHON` to a suitable interpreter's path, in the environment Claude Code starts from. Without a usable Python, each hook prints one line to stderr, and the session runs with no rule text and no checks.

## Install

```sh
claude plugin marketplace add synapseradio/.claude
claude plugin install epistemic-marks@claude-root
```

The first command adds this repository as a plugin marketplace named `claude-root`. The second installs the plugin from it. To load the plugin, run `/reload-plugins` in an open session or restart Claude Code.

If the first command fails to clone over SSH, set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` and run it again.

## What it does

The plugin ships its rule text and its hooks together, so it works with nothing else installed.

- At every session start and subagent start, it adds the rule text to the context. A subagent is an agent that another agent starts.
- When a reply ends with a mark in it, the Stop hook blocks the reply once and lists each marked line with the step that resolves it. Any mark left after the rewrite is shown to you, and the reply ends.
- When a subagent finishes, the SubagentStop hook checks its report the same way. It leaves the caller's mark and the standing question in place, and asks the subagent to carry them in its report to the agent that started it.
- After each batch of tool calls, the PostToolBatch hook shows any marked line written since your last message. It never blocks, and it shows each line once per session.

## Turn it off

```sh
claude plugin disable epistemic-marks@claude-root
```

Then reload, as after installing. `claude plugin enable epistemic-marks@claude-root` turns the plugin back on, and `claude plugin uninstall epistemic-marks@claude-root` removes it.

## State and configuration

To show each marked line only once, the hooks keep a record of the lines they have shown. The record holds a SHA-256 fingerprint of each line and never its text, and entries older than a day are removed.

These environment variables configure the plugin, and nothing else does.

- `EPISTEMIC_MARKS_PYTHON` names the Python that runs the hooks, tried before every other name.
- `VERIFY_MARKS_STATE_DIR` names the directory for the record. Without it, the record goes to `verify-marks` under `CLAUDE_PLUGIN_DATA`, or else to `epistemic-marks-verify-marks` in the system temporary directory.

The plugin delivers its rule text as shipped, from `rule-text/epistemic-marks.md`, and no setting points it at another file. An update replaces that file, so a local edit to it is lost.

The plugin reads none of your configuration and no other plugin. The hooks that check replies read the session transcript, at the path Claude Code passes them.
