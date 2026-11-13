# Warden

Warden is a Claude Code plugin that checks each shell command, file read, file search, and subagent spawn before Claude Code makes it, and refuses or asks you about the risky ones.

Each guard is a `PreToolUse` hook: a script Claude Code runs before a tool call, which can let the call through, refuse it, or show you a permission prompt. A refused call never runs, and Claude Code receives the guard's reason. A call that no guard matches runs as it would without warden.

## Install

Run these two commands in Claude Code, with the path of your copy of this repository:

```console
/plugin marketplace add <path to your copy of this repository>
/plugin install warden@claude-root
```

`claude-root` is the marketplace this repository publishes. If your own settings already run any of these guards, remove those entries: two copies of a guard both run, and you are refused twice for one command.

`deny-inplace-stream-edit` enforces a decision this repository records as the `exact-edits` rule, which ships separately from this plugin. Install the rule alongside the plugin. Without it, nothing announces the decision, and the first sign of it is a refused command.

## What it guards

"Watches" names the Claude Code tool each guard checks. "Bash" means shell commands.

| Guard | Watches | What it stops | Decision |
| --- | --- | --- | --- |
| `block-secret-leaks` | Bash | Printing an environment variable named like a key, token, password, or credential, or dumping the whole environment | Refuses |
| `block-secret-file-reads` | Bash, Read | Reading a file where credentials live, such as SSH keys, `~/.aws`, or a `.env` file, or a path in your banned-reads file | Refuses |
| `deny-inplace-stream-edit` | Bash | Editing a file in place with `sed -i` or `awk -i inplace` | Refuses |
| `ask-remote-data-send` | Bash | A `curl` that sends data or a file, or uses a write method such as `POST`, to a host other than your own machine | Asks |
| `ask-fetch-and-run` | Bash | Downloading a package and running it in one step, such as `npx`, `uvx`, or `docker run` | Asks |
| `deny-unpinned-bunx` | Bash | A `bunx` or `bun x` run whose package names no version; `@latest` counts as one | Refuses |
| `deny-sleep` | Bash | Waiting on `sleep` | Refuses |
| `deny-rm` | Bash | An `rm` that would remove anything git cannot restore, or that follows another step of the same command | Refuses |
| `deny-bulk-home-search` | Bash, Grep, Glob | A file search starting at the disk root, at the folder holding every home directory, or at your home directory itself | Refuses |
| `deny-eval` | Bash | Running `eval` | Refuses |
| `deny-shell-c` | Bash | Running `bash`, `sh`, `zsh`, `dash`, or `ksh` with `-c` | Refuses; asks for `zsh -ic` |
| `deny-indirect-execution` | Bash | Command substitution `$( )`, backticks, process substitution `<( )`, `>( )`, or `=( )`, and subshells; a plain `$( )` holding `pwd`, `git rev-parse`, `git branch --show-current`, or `wt stack base` passes, and so does either git query with `-C <path>` after `git`, where the path is a literal of letters, digits, and `_./=:@%+,-` or a double-quoted string opening with `$HOME/` | Refuses |
| `ask-git-amend` | Bash | `git commit --amend` | Asks |
| `deny-unsafe-soft-reset` | Bash | A `git reset --soft` that could lose work or rewrite published history; one over unpushed commits on a feature branch, as the command's first step, passes | Refuses |
| `deny-hook-covered-check` | Bash | Running by hand a check the repository's git hooks already run on commit or push; test runs pass | Refuses |
| `deny-unset-model` | Agent | A subagent spawn that names no model, unless it is a fork or its agent definition pins one, and a `critic` or `Plan` spawn on haiku | Refuses |

## When a guard steps in

A refusal tells Claude Code why the guard refused and, where one exists, a safer way to do the same step. If you meant the command, run it yourself in your own terminal: the guards check only the calls Claude Code proposes, never what you type.

An ask shows you the usual permission prompt, and you approve or decline the command there.

## Add your own sensitive paths

`block-secret-file-reads` covers the places credentials live on any machine. To keep other paths out of reach, list them in `warden/banned-reads.conf` inside your Claude directory, which is `~/.claude` or `$CLAUDE_CONFIG_DIR` where that is set:

```text
# the private half of my shell configuration
my-private-store/
# the folder our deployment keys land in
deploy-keys/
# broad enough that warden leaves it to you
credentials
```

Each line holds one piece of a path or filename, matched literally, so nothing needs escaping. A line starting with `#` is a comment. Words like `credentials` and `secrets` appear in too many harmless paths for warden to refuse them by default, so this file is where you turn them on. A listed fragment stops only a command or read that would open a matching file; a command that merely mentions it runs.

The file takes effect on the next call. Set `WARDEN_BANNED_READS` to keep it at another path. The file only adds: an empty, broken, or missing file leaves the built-in coverage as it ships.

One file needs this list. Claude Code can fetch your API key by running a program of your own, named as `apiKeyHelper` in your settings, and that program and the file it reads can carry any name. Warden catches them only when they sit in a `private` folder inside a dotfiles checkout or carry a secrets name such as `secrets.env`. Otherwise, add their names to `banned-reads.conf`.

## Check that the guards are live

A guard that breaks lets commands through without a word, so check after installing and after any change to your configuration.

1. Run `/hooks` and open `PreToolUse`. Each guard appears against the tool it watches, labelled `[plugin:warden]`.
2. From this plugin's directory, run `bash scripts/preflight.sh`. It sends sample calls through the guards and prints one line per case, then `Every guard decided as expected.` when all of them match. It has no cases for `ask-fetch-and-run` or `deny-rm`.
3. A line starting with `FAIL` names the guard and what it decided instead. Treat that guard's protection as absent until the line reads `ok` again.

## Limits

- A guard recognizes the shape of a command. It guards against accidents; someone set on getting around it can write the same command another way.
- You cannot switch off a single guard. `disableAllHooks` turns off every hook from every source. To drop one guard, uninstall the plugin, or copy it and remove that guard's entry from `hooks/hooks.json`.
- The guards see only the tool calls Claude Code makes, not your terminal, your editor, or anything else on the machine.

## Where the details live

- `hooks/<guard>.sh`: the header comment states exactly what the guard matches, where in a command it looks, and what it lets through.
- `tests/<guard>.bats`: one named case for each command the guard refuses, asks about, or lets through. Run one guard's cases with `bats tests/<guard>.bats`.
- `hooks/hooks.json`: which tool each guard watches.
