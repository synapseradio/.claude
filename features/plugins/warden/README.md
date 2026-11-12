# Warden

Before Claude Code runs a shell command on your machine, it shows the command to the guards in the table below that watch commands. Most of them refuse a command outright and say why. The others pause and ask you first. Everything else runs untouched. One of them also checks the path when Claude Code opens a file directly, which is a second layer behind whatever your own settings already refuse, and another also checks where Claude Code's own file search tools start. The last guard in the table checks each subagent Claude Code spawns.

## What each guard stops

| Guard | What it stops | What you see |
| --- | --- | --- |
| `block-secret-leaks` | A command that would display a password, key, or token | Refused |
| `block-secret-file-reads` | A command that would open a file holding your credentials | Refused |
| `deny-inplace-stream-edit` | A command that rewrites a file in a way that can quietly damage it | Refused |
| `ask-remote-data-send` | A command that would upload data to another machine | A prompt asking you to approve |
| `ask-fetch-and-run` | A command that downloads a package and runs it in the same step | A prompt asking you to approve |
| `deny-unpinned-bunx` | A `bunx` or `bun x` command whose package names no version | Refused |
| `deny-sleep` | A command that waits on a timer | Refused |
| `deny-rm` | A command that deletes with `rm` something git cannot bring back, or runs `rm` after another step | Refused |
| `deny-bulk-home-search` | A file search that walks your whole home directory or the whole disk | Refused |
| `deny-eval` | A command that runs `eval` | Refused |
| `deny-shell-c` | A command that runs a shell with `-c` | Refused, or a prompt for `zsh -ic` |
| `deny-indirect-execution` | A command substitution, backticks, a process substitution, or a subshell | Refused |
| `ask-git-amend` | A command that amends a commit with `git commit --amend` | A prompt asking you to approve |
| `deny-unsafe-soft-reset` | A `git reset --soft` that could lose work or rewrite published history | Refused |
| `deny-hook-covered-check` | A command that runs by hand a check the repository's git hooks already run | Refused |
| `deny-unset-model` | A subagent spawned without a model, and a critic or planner spawned on haiku | Refused |

`block-secret-leaks` watches for commands that print the hidden values your shell keeps for you, the ones named like a key, a token, a password, or a credential. It also refuses a command that would list every one of those values at once.

`block-secret-file-reads` watches for commands that open the files where credentials live: your SSH keys, which prove your identity to other machines; your cloud and encryption directories; your cluster configuration; the `.env` files a project uses to hold its own passwords; a `private` folder inside a dotfiles checkout, where shell setups usually keep the functions that hand out keys; and files named for the secrets they hold, such as `secrets.env`, `secrets.sh`, or anything ending in `.secrets`. This guard also checks the file path when Claude Code opens a file directly rather than through a shell command.

`deny-inplace-stream-edit` refuses a search-and-replace that edits a file in place. That kind of edit reports nothing when its search text does not match, so a small mistake in the search text can rewrite the wrong part of the file and leave no sign of it. Claude Code has two other ways to edit a file that match exactly and stop with an error when they do not, and the refusal points at those.

`ask-remote-data-send` steps in when a command would send a file or a block of data to a machine on the network. It does not refuse. It asks, and you decide. Fetching something to read, such as a page of documentation, does not prompt, and neither does sending data to a program running on your own machine.

`ask-fetch-and-run` steps in when a command downloads a package from a registry and runs it at once: `npx`, `npm exec`, `npm x`, `npm create`, `npm init` with an initializer name, `pnpm dlx`, `pnpx`, `pnpm create`, `yarn dlx`, `yarn create`, `bun create`, `bx`, `uvx`, `uv tool run`, `pipx run`, `docker run`, and `podman run`. It does not refuse. It asks, and the message it carries tells Claude Code to state the package, the version the command pins, what it executes, and which installed tool falls short of the step, and to pin a version. `bunx` and `bun x` do not prompt here; `deny-unpinned-bunx` judges them.

`deny-unpinned-bunx` refuses a `bunx` or `bun x` command whose package argument names no version, because `bunx` downloads the package and runs it in the same step, so a bare name runs whatever the registry serves at that moment. `bunx cowsay` is refused. `bunx cowsay@1.5.0`, `bunx @scope/pkg@2.0.1`, and `bunx cowsay@latest` run. It skips the options that come before the package, such as `--bun` and `--silent`, and the value of a few options that take one, such as `--cwd`. When `-p` or `--package` appears, the guard judges that value in place of the word after the options, which then names a binary, and a command with several is refused if any one names no version. A scoped package's leading `@` marks the scope and not a version. It covers the same command positions as `deny-rm`, and a command with no package, such as `bunx --version`, is left alone. The refusal says to run `bunx <pkg>@<version>`, pinned or at `@latest`, and to state the package, the version, what it executes, and which installed tool falls short of the step.

`deny-sleep` refuses `sleep` wherever it starts a command, a loop body included. A sleep holds the session on a guess at how long something takes. The refusal points at running the command in the background, which resumes the session with a completion notice when the command exits, or at reading the log once with a command that exits.

`deny-rm` lets `rm` run when git can restore everything it removes: each path it names is tracked, identical to the last commit, with nothing staged or modified, or the path does not exist. A directory runs only when every file beneath it is committed and unchanged and nothing beneath it is untracked or ignored, so a `__pycache__` folder or a nested repository holds it back. Each path is judged in the repository that holds it, and a relative path resolves against the directory the command starts in. The guard refuses when it cannot tell what `rm` would remove: a path outside any git repository, a path with a wildcard, a variable, a command substitution, a brace expansion, or a `~`, an `rm` that gets its paths from `xargs` or `find -exec`, a command that changes directory before the `rm`, and a git that fails or does not answer within four seconds. It looks at `rm` wherever it starts a command: at the beginning, after `&&`, `||`, `;`, `|`, or a new line, inside a subshell or `$(`, after `sudo`, `command`, `xargs`, `env`, or `exec`, inside a `bash -c` string, and behind `find -exec`. The refusal names the path it held back and points at `trash <path>`, which moves the path to the Trash where it can be recovered.

The guard reads the disk before the command runs, so it refuses any `rm` that follows another step of the same command, whatever the path: `mkdir d && echo x > d/f && rm -r d` and `npm run build && rm -rf dist` are refused even where `d` or `dist` would be committed and unchanged, because the earlier step may have written what `rm` then removes. A step is any other command or redirect before the `rm`, split at `&&`, `||`, `;`, `|`, `&`, and new lines, and inside a subshell, `$(`, or a `bash -c` string. An `rm` that comes first is judged as above, and `rm a && rm b` runs when each is restorable, since `rm` writes nothing. The refusal says to send output known to be throwaway to `/dev/null` in place of writing a file and deleting it, and otherwise to use `trash <path>`.

`deny-bulk-home-search` refuses a file search that starts at the top of the disk, at the folder that holds every user's home, or at your home folder itself. It covers `find`, `fd`, `rg`, a recursive `grep`, `ag`, `ack`, `tree`, `du`, a recursive `ls` or one over a wildcard at the top of home, `locate`, and `mdfind` without `-onlyin`, along with Claude Code's own Grep and Glob tools. A search that names no starting folder starts in the current one, so the guard also refuses it when the current folder is one of those. A search inside one folder of your home runs untouched. The refusal points at searching the one folder that holds what is wanted, or at the tool's documentation.

`deny-eval` refuses `eval` wherever it starts a command, with the same reach as `deny-rm`: after a separator, in a subshell or `$(`, behind a wrapper, and inside a `bash -c` string. The refusal points at writing the step as a script file in the scratchpad and running that file, or running the command directly. `git log --eval`, `echo eval`, and `eval` inside quotation marks run untouched.

`deny-shell-c` refuses a command that runs `bash`, `sh`, `zsh`, `dash`, or `ksh` with `-c`, alone or in a flag cluster such as `-lc` or `-xc`, because the string after `-c` runs without ever standing as a command the other guards read. The refusal says to write the step as a script file in the scratchpad and run that file, with the shell under test where the point is how that shell behaves. `zsh` with both `-i` and `-c`, as in `zsh -ic '<command>'`, asks in place of refusing, for a command-line tool whose credentials load only in an interactive shell. Other interpreters, `grep -c`, and a shell that runs a script file run untouched.

`deny-indirect-execution` refuses a command that runs text not standing as a command of its own: a command substitution `$( )`, backticks, a process substitution `<( )` or `>( )`, zsh's `=( )`, and a subshell `( )` where a command starts. The shell runs these inside double quotes and inside a here-document whose delimiter is unquoted, so the guard catches them there too. Single quotes, a backslash, a here-document with a quoted delimiter such as `<<'EOF'`, and a comment leave them as plain text. Arithmetic `$(( ))` and `(( ))`, an array such as `args=(a b)`, a glob qualifier such as `*(.)`, and parentheses in a quoted pattern run untouched. One kind of substitution runs too: a read-only query, `pwd`, `git rev-parse`, `git branch --show-current`, or `wt stack base`, written with no quote, second step, redirect, or nested substitution. The refusal says to run each step as its own command and pass its output on as a literal value, to commit a multi-line message with `git commit -F <file>`, or to write a script file in the scratchpad and run it.

`ask-git-amend` steps in when a command runs `git commit` with `--amend`, wherever `--amend` stands and whatever options precede the subcommand, as in `git -C <path> commit --amend`. It does not refuse. It asks, and the message it carries says that after a hook rejects a commit, the cause is fixed and the commit made anew rather than amended. A commit message that mentions `--amend` does not prompt.

`deny-unsafe-soft-reset` lets `git reset --soft` run, so a background agent can squash its own branch, and refuses every soft reset that could lose work or rewrite history others rely on. A soft reset runs only when all of these hold: it names exactly one revision, with no pathspec and no second mode flag such as `--hard`, `--mixed`, `--merge`, or `--keep`; the repository has no rebase, merge, cherry-pick, or revert in progress; HEAD is on a branch that is not the default branch, which is the one `origin/HEAD` names, or `main` and `master` where `origin/HEAD` is unset; the revision resolves to a commit that is an ancestor of HEAD; and none of the commits between the revision and HEAD is reachable from a remote-tracking ref, so only unpushed commits are uncommitted. `git reset --soft HEAD~2` on an unpushed feature branch runs. The same command on `main`, on a detached HEAD, in the middle of a rebase, or after the branch was pushed is refused. The repository is the one the command's `-C <path>` names, or the directory Claude Code works in. The refusal names the condition that failed and points at `wt -C <worktree> step squash <target>`, which squashes a branch without touching published history.

The guard refuses whenever it cannot tell what the reset would do: a revision or `-C` path with a wildcard, a variable, a command substitution, a `~`, or a reflog brace such as `HEAD@{1}`; a git option before the subcommand other than `-C`, such as `--git-dir`, `--work-tree`, or `-c`; a `GIT_` variable set for the command; a command that changes directory, with `cd`, `pushd`, or `env -C`; a relative `-C` path when no working directory is known; and a git that fails or does not answer within four seconds. It reads the repository before the command runs, so it also refuses a soft reset that follows another step of the same command, such as `git push; git reset --soft HEAD~1`, because that step may have published the commits or switched branches. A soft reset that comes first runs, and steps after it, such as `git reset --soft origin/main && git commit -m "squash"`, are no concern of this guard. It looks at `git` wherever it starts a command, with the same reach as `deny-rm`: after a separator, in a subshell or `$(`, behind `env`, `sudo`, `command`, or `exec`, and inside a `bash -c` string. A reset without `--soft`, `git commit -m "git reset --soft"`, and `echo` of the words stay untouched.

`deny-hook-covered-check` refuses a command that runs a check by hand when the repository you are working in already runs that check from a git hook on commit or push. The hook runs it on every commit anyway, so the refusal says to commit and let the hook run it. The guard finds the repository from the directory Claude Code works in, and follows a `cd` in the command into another repository. It reads the pre-commit and pre-push hooks from `lefthook.yml` and `lefthook.yaml` (and their `.lefthook` and `-local` variants), from the `entry:` lines of `.pre-commit-config.yaml`, from `.husky/pre-commit` and `.husky/pre-push`, and from the executable `pre-commit` and `pre-push` files in the git hooks directory, which follows `core.hooksPath`. A hook that `.pre-commit-config.yaml` takes from a remote repository names no command there, so it is not read, and neither are lefthook `scripts:` and YAML written in flow style or anchors.

A command counts as a hook's check in one of three ways. A package script matches when the package manager, any `--filter` or `--cwd` scope, and the whole script name agree, so `bun run lint` and `bun lint` match a hook running `bun run lint`, while `bun run lint:fix` and `npm run lint` do not. A tool with a subcommand matches on the program and the subcommand, so `biome check src` matches a hook running `biome check --staged`, while `biome lint` does not. A tool without a subcommand matches on the program and the flags the hook passes, so `tsc --noEmit -p tsconfig.json` matches a hook running `tsc --noEmit`, while `tsc --version` does not; flags that only change how a tool runs, such as `--fix` and `--write`, are not required. A runner in front, such as `bunx`, `npx`, `uv run`, or `python -m`, is looked through on both sides.

Test runs stay allowed even when a hook runs them: a script named `test` or `test:<something>`, `bun test`, `npm test`, `cargo test`, `go test`, and `jest`, `vitest`, `bats`, `pytest`, and the other test runners. So do general-purpose programs such as `git`, `node`, `python`, `bash`, and `echo`, a build tool like `make` with no target, and the hook runners `lefthook`, `husky`, and `pre-commit`. A directory that is no repository, a repository with no hook configuration, and a configuration the guard cannot read all pass without a word. The guard stops reading after two seconds, well inside the five-second limit.

`deny-unset-model` refuses a subagent spawn that names no model. Without one, a subagent runs on the model its definition names, and otherwise on the model of the main conversation, so a session on the most expensive model spawns every helper on it too. A fork passes, since it shares the main conversation's model by design. So does a spawn of an agent whose definition pins a model other than `inherit`. The guard finds that definition in your Claude directory's `agents/`, in the project's `.claude/agents/`, or, for a name like `my-plugin:reviewer`, in the installed plugin's `agents/`. The order Claude Code resolves a subagent's model in is documented at <https://code.claude.com/docs/en/sub-agents.md#choose-a-model>.

The same guard refuses a spawn of a `critic` or a `Plan` agent that runs on haiku, whether the call names haiku or names no model and the agent's definition pins haiku. Critics and planners run on sonnet or opus, and the refusal says so. The built-in `Plan` agent has no definition file, so only a model named on the call can put it on haiku. Its refusal when no model is named is the unset-model one above.

## What still runs normally

These guards are built to stay out of the way. All of the following keep working:

- Setting a value for one command, as in `env FOO=bar npm test`
- Turning on shell options at the top of a script
- Reading a project file, including one named `.envrc`
- Search-and-replace that only prints its result instead of saving it
- Downloading a page to read
- Sending data to a program running on your own machine
- A command that merely mentions a blocked pattern inside quotation marks
- `/private/tmp` and `/private/var`, which on a Mac are the real `/tmp` and `/var`
- A `private` folder in a project, such as `src/private`
- A script that manages secrets rather than holding them, such as `rotate-secrets.sh`
- An example or template beside a real secrets file, such as `secrets.env.example`
- A `.secrets.baseline`, the record a secret-scanning tool keeps
- A word that only contains `sleep`, such as `sleepy`, or `sleep` inside quotation marks
- `git rm`, `npm rm`, `bun rm`, `pnpm rm`, `docker rm`, `rmdir`, and `trash`, and the word `rm` as an argument, as in `grep -n rm file`, or inside quotation marks
- `bunx` and `bun x` at a pinned version or `@latest`, and package commands that fetch nothing to run, such as `bun install`, `npm install`, and `docker build`
- `git reset --soft` on a feature branch, back over commits no remote-tracking ref holds, as the first step of its command
- `zsh -ic '<command>'` for a tool whose credentials load only in an interactive shell, after you approve the prompt
- A plain read-only query in `$( )`, as in `git -C "$(git rev-parse --show-toplevel)" status`, and `$( )` or backticks inside single quotes or a `<<'EOF'` here-document
- A subagent spawn that names its model, and any fork
- A critic or planner spawned on sonnet or opus, and haiku for any other agent
- A check no git hook runs, a test run, a script whose name only starts like a hook's (`bun run build` against a hook running `bun run build:check`), and any command in a directory outside a repository
- A search inside one folder of your home, such as `find ~/projects/app -name x`, and a plain `ls ~`

## Adding your own sensitive paths

The guards cover the places credentials live on every machine. Anything else you want kept out of reach goes in a file of your own, inside your Claude directory:

```console
~/.claude/warden/banned-reads.conf
```

Put one piece of a path or filename on each line. It is matched exactly as you write it, so nothing needs escaping, and a line beginning with `#` is a note to yourself:

```text
# the private half of my shell configuration
my-private-store/
# the folder our deployment keys land in
deploy-keys/
# broad enough that we leave it to you
credentials
```

That last line is the kind of thing this file is for. Words like `credentials` and `secrets` appear in too many harmless paths to refuse for everybody, so they are yours to switch on rather than ours to impose. A banned fragment still only stops a command that would *read* the file, so a line mentioning `credentials` in passing runs as usual.

The file takes effect on the next command. To keep it somewhere else, set `WARDEN_BANNED_READS` to the path you prefer.

Your file only adds. Nothing you write in it can switch off what the guards already cover, so a file that is empty, half-written, or missing altogether leaves you exactly as protected as a fresh install.

This plugin ships no path belonging to any one person's machine, which is why your own belong here rather than inside it.

## One thing no guard catches

Claude Code can be set up to fetch your API key by running a small program of your own, named in your settings as an `apiKeyHelper`. That program, and any file it reads the key from, can be called anything at all. No pattern can recognize it by name: every pattern wide enough to find a file called `get-key` also refuses a keyboard layout, a keychain export, and the list of hosts your SSH client trusts.

So the guards reach that file in two situations and no others. If it sits in a `private` folder inside a dotfiles checkout, or if it is named for the secrets it holds, the patterns already cover it. Otherwise nothing here protects it, and the way to close that gap is to write its name into your `banned-reads.conf`. This is the one place where leaving the file empty leaves something genuinely uncovered.

## Installing

Run these two commands in Claude Code, replacing the path with wherever you keep your copy of this repository:

```console
/plugin marketplace add <path to your copy of this repository>
/plugin install warden@claude-root
```

The name `claude-root` is the marketplace this repository publishes. If your own configuration already runs any of these guards, take those entries out when you install. Two copies of one guard both run, so you would be refused twice for the same command.

## Checking that the guards are live

Do this after installing, and again after any change to your configuration.

1. Run `/hooks` and open `PreToolUse`. One entry should appear against the Bash tool for each guard in the table above that watches commands, and one each against the Read tool, the Grep and Glob tools, and the Agent tool, each labelled `[plugin:warden]`. That label is what tells you the guard comes from this plugin.
2. From this plugin's directory, run `bash scripts/preflight.sh`. It puts a set of commands through the guards and prints one line for each. Every line should begin with `ok`, and the last line should read that every guard decided as expected.
3. If any line begins with `FAIL`, that guard is not doing its job. The line names the guard and what it decided instead. Treat the protection as absent until it reads `ok` again.

The check in step 2 exists because a guard that stops working says nothing. It goes quiet, commands start running, and nothing announces the change. Running the check is how you find out.

## If a guard stops something you meant to do

Read the refusal, which names what it matched and why. If you meant the command, run it yourself in your own terminal. These guards apply to commands Claude Code proposes, and never to what you type directly.

## Limits worth knowing

A guard recognizes the shape of a dangerous command. Somebody determined to get around one could write the same command differently, so treat these as protection against an accident rather than against an adversary.

You cannot switch off one guard. The only setting that turns hooks off, `disableAllHooks`, is all or nothing, and it silences every hook you have from every source, not only these. To stop a single guard, uninstall this plugin or make your own copy and remove that guard's entry from `hooks/hooks.json`. Both of those leave a visible trace, which for a safety control is the point.

The guards see a command only when Claude Code is about to run it. They do not watch your terminal, your editor, or anything else on the machine.

## The rule behind the in-place edit refusal

The refusal of a search-and-replace that saves in place is a house decision, written down in this repository as a rule named `exact-edits`, which is delivered separately from this plugin. This plugin holds no copy of that rule and does not need it: each guard states its whole reason in the message you receive.

What you lose by installing the guard without the rule is the warning. Nothing tells you the decision was made, so the first you hear of it is a command that will not run. If you install the guard, install the rule alongside it.
