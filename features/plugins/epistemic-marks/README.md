# epistemic-marks

epistemic-marks stops Claude Code from ending a reply on a claim nobody has checked, and from handing on a guess as if it were a finding.

The plugin adds rule text, a section of instructions, to every session. It teaches Claude to end each unverified clause with a mark, a short token such as `[?]`. When a reply ends with a mark still in it, a hook sends the reply back once. When it ends with a guess written in words, the hook sends it back until the guess is marked or gone. Claude then replaces each mark with a source, narrows the claim to what the source backs, or removes the claim.

Wording does not count as a mark. A sentence that says "my guess", "probably" or "I haven't checked this, but" is sent back the same way, to be checked or to be stated plainly with the mark.

> **An AI agent installing this plugin for someone?** Follow [SETUP.md](SETUP.md). It gives each command with its expected output, and names the steps to hand to the person.

## Marks

| Mark | Name | Resolved by |
| --- | --- | --- |
| `[?]` | the unsourced mark | finding a source for the claim |
| `[.?]` | the secondhand mark | checking what another agent, a tool, or a person reported |
| `[^?]` | the caller's mark | a decision from the agent that started this one |
| `[!?]` | the standing question | a decision only a person can make |

A mark inside a fenced code block, or inside a longer code span, does not count. Nor does a mark on a line that names it, where the mark sits alone in a code span, alone in quotes, or straight after its name, as in "the unsourced mark, `[?]`". That line talks about the mark rather than claiming under it.

## A guess in words

The hooks also read for a guess written in words with no mark and no source in the same sentence. They flag three things:

- wording of doubt, such as "my guess", "I suspect", "probably", "it seems", "that should fix it", or "as far as I know";
- a status written as a sentence or a label, such as "I haven't checked this, but", "(unverified)", or "these are guesses";
- a sentence that builds on a marked or guessed claim without a mark of its own, such as one that starts "That would" or "So" straight after it.

A sentence passes when it ends a clause with a mark, or when it gives a source, a path with a line number or a URL. Fenced code, code spans, quoted text, block quotes and questions are not read. A sentence that names a mark in words is not flagged. You see it in a notice instead.

This check is a word list, and a word list has limits. It leaves "may", "should" and "must" alone outside a few fixed phrases, because the same words also give permission or state a requirement. It cannot see a guess stated as plain fact. The rule text covers both: it tells Claude to mark every claim it did not see evidence for in the session, whatever the wording.

## Requirements

The plugin runs on Claude Code 2.1.268 or later, the oldest version tested, and on Python 3.14 or later, provisioned by [uv](https://docs.astral.sh/uv/).

The hooks run through `uv run --python 3.14 --no-project`, so a 3.14 interpreter runs them even where the system `python3` is older. The launcher looks for uv on the path, then at `bin/uv` in the plugin's data directory (`CLAUDE_PLUGIN_DATA`, which survives plugin updates). If it finds none, it installs uv with [Astral's standalone installer](https://docs.astral.sh/uv/getting-started/installation/) into that `bin`, without editing any shell profile, and uses that copy. A Python 3.14 that uv downloads and uv's cache go in the same data directory, so nothing is installed in your home directory. Where `CLAUDE_PLUGIN_DATA` is unset, the launcher takes the failure path below. If the installer cannot run or fails, the session runs with no rule text and no checks, and each hook says so to the model and the user alike: it prints a JSON output naming uv on stdout and exits 0, in the form the event reads (`additionalContext` on SessionStart, SubagentStart and PostToolBatch, a deny reason on PreToolUse, a block reason on Stop and SubagentStop), with the same text as `systemMessage`. A Stop or SubagentStop already continued by that failure says nothing more. The launcher never falls back to the system Python.

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
- When a reply ends with a mark or a guess in words in it, the Stop hook blocks the reply and lists each line with the step that resolves it. A mark left after the rewrite is shown to you, and the reply ends. A guess in words left after the rewrite blocks the reply again, each time, and is shown to you each time.
- When a subagent finishes, the SubagentStop hook checks its report the same way. It leaves the caller's mark and the standing question in place, and asks the subagent to carry them in its report to the agent that started it.
- After each batch of tool calls, the PostToolBatch hook shows Claude any marked line or guess in words written since your last message, and tells it to check the claim before the next step. It never blocks, and it shows each line once per session.
- When Claude starts a subagent, the PreToolUse hook reads the prompt it wrote. If the prompt hands the subagent a guess in words, the hook denies the call and Claude rewrites the prompt. A marked claim in a prompt passes, because the mark tells the subagent the claim is unverified.

## Turn it off

```sh
claude plugin disable epistemic-marks@claude-root
```

Then reload, as after installing. `claude plugin enable epistemic-marks@claude-root` turns the plugin back on, and `claude plugin uninstall epistemic-marks@claude-root` removes it.

## State and configuration

To show each marked line only once, the hooks keep a record of the lines they have shown. The record holds a SHA-256 fingerprint of each line and never its text, and entries older than a day are removed.

These environment variables configure the plugin, and nothing else does.

- `VERIFY_MARKS_STATE_DIR` names the directory for the record. Without it, the record goes to `verify-marks` under `CLAUDE_PLUGIN_DATA`, or else to `epistemic-marks-verify-marks` in the system temporary directory.

The plugin delivers its rule text as shipped, from `rule-text/epistemic-marks.md`, and no setting points it at another file. An update replaces that file, so a local edit to it is lost.

The plugin reads none of your configuration and no other plugin. The hooks that check replies read the session transcript, at the path Claude Code passes them. Every check is a local Python script. No hook calls a model.
