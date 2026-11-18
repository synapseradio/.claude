# epistemic-marks

epistemic-marks gives you replies from Claude Code where you can see what Claude checked and what it is still guessing. Each statement Claude has not checked carries a small mark, and before a reply reaches you, Claude checks the statement, cuts it, or moves it to the top where you meet it first.

It suits anyone who acts on what Claude tells them: a diagnosis, an answer from research, a review of a change.

> **An AI agent installing this plugin for someone?** Follow [SETUP.md](SETUP.md). It gives each command with its expected output, and names the steps to hand to the person.

## What you get

- **Sources beside findings.** A statement Claude checked comes with where it found the answer, such as the file and line it read.
- **Guesses in plain sight.** A statement Claude has not confirmed carries a mark, so you can tell a guess from a finding.
- **Open questions up front.** Whatever Claude could not settle sits at the top of the reply, ahead of everything else.
- **Your decisions stay yours.** A choice only you can make comes to you as a question.
- **Helpers held to the same standard.** Claude can hand part of a task to a helper agent, a second Claude it starts. Each helper gets the same instructions, and its report is checked before it comes back. Instructions to a helper that pass on a guess in words go back to Claude for a rewrite first.
- **Another route before giving up.** Where a permission check stops Claude from opening a web page, Claude tries another way to reach it before marking the statement. Where you refuse a tool yourself, Claude asks you before trying another way.

## What a reply looks like

| | The same lines |
| --- | --- |
| Without the plugin | My guess is the editor builds these files without that config. That would drop the Node types, which matches the errors. |
| With the plugin, before checking | The editor builds these files without that config [?]. That drops the Node types [?], which matches the errors [?]. |

Claude then works through the marks. A statement it confirms gets its source beside it. A statement it cannot confirm is narrowed to what it found, or cut.

## The marks

| Mark | What it tells you | What happens to it |
| --- | --- | --- |
| `[?]` | Claude has no source for this statement. | Claude looks for one. |
| `[.?]` | Claude got this from someone else, such as a tool, a person, or a helper agent, without a source. | Claude checks it. |
| `[^?]` | This is a decision for whoever handed Claude the task. | Claude asks you, or a helper agent passes it to the Claude that started it. |
| `[!?]` | Only a person can make this decision. | It reaches you as a question. |

## How it works

Claude receives a short set of instructions at the start of every session and every helper agent. Before a reply reaches you, the plugin reads it. While the reply still holds a mark, or a guess in words such as "probably" or "my guess is", it goes back to Claude with each line to fix. A mark Claude cannot clear may stay, at the top of the reply. Between steps of a task, Claude is reminded of each unchecked statement before it builds on one.

The checks run on your computer, read the session's conversation there, and call no AI model. To show each line only once, the plugin keeps a fingerprint of each line it has shown, never the text. [CONFIGURATION.md](CONFIGURATION.md) says where that record lives.

## Good to know

- **Checking takes extra time.** A reply can go back up to five times in a turn, and each rewrite is one more response from Claude. After the fifth, the plugin shows its findings to you and to Claude without sending the reply back.
- **The check reads words.** It sends back a "probably" written for a good reason, and it cannot see a guess written as plain fact; the instructions ask Claude to mark that case too. A source Claude names is not checked against what it says.
- **First use downloads Python.** Where your computer lacks them, the plugin downloads uv, a tool that installs Python, and Python 3.14 into its own data folder, which needs an internet connection once. If that fails, the plugin runs without instructions or checks and tells you so.

## Install

The plugin needs Claude Code 2.1.268 or later.

```sh
claude plugin marketplace add synapseradio/.claude
claude plugin install epistemic-marks@claude-root
```

The first command adds this repository as a source of plugins, called a marketplace, named `claude-root`. The second installs the plugin from it. Then run `/reload-plugins` in an open session, or restart Claude Code.

If the first command fails with an SSH error, run it again as:

```sh
CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1 claude plugin marketplace add synapseradio/.claude
```

## Turn it off

```sh
claude plugin disable epistemic-marks@claude-root
```

Then reload, as after installing. `claude plugin enable epistemic-marks@claude-root` turns the plugin back on, and `claude plugin uninstall epistemic-marks@claude-root` removes it.

## More detail

- [DESIGN.md](DESIGN.md): how each check works, why it works that way, and its measured limits.
- [CONFIGURATION.md](CONFIGURATION.md): where the plugin keeps its record, and the setting that moves it.
- [rule-text/epistemic-marks.md](rule-text/epistemic-marks.md): the instructions Claude receives, word for word.
