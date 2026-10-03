<!-- rule: bash-commands -->

## bash-commands

For every Bash tool call, optimize for a command the session's allow rules match part by part, running only the programs its text names.

### The shape

Hold every part of a compound command as matched against the allow rules on its own, split at `&&`, `||`, `;`, `|`, `&`, and newlines. Give each call the fewest parts its step needs. Run two steps in one call only where they share shell state. Write every redirect target and every `tee` target as an absolute path. Run git in another directory with `git -C <path> <subcommand>`.

Keep a leading `~` out of every redirect target. Keep `cd` out of every call that holds a git command.

### Programs

Run a repository's tools through the scripts its package.json defines. Where a tool lacks a script, call it at `node_modules/.bin/<tool>`. Where a step needs a script of its own, write it to a file in the scratchpad through Write, then run that file. Run a shell with `-c` only to test how that shell behaves.

A fetch-and-run command is one that resolves a package from a registry and executes code from it in the same step, `npx` for one. Before every fetch-and-run call, state in the message the package, the version the command names, what it executes, and which installed tool falls short of the step. Run `bunx` and `bun x` on your own judgment, at a pinned version or `@latest`. Run every other fetch-and-run command only on the user's approval. Pin the package version in every other fetch-and-run command.

Run a fetch-and-run command at an unpinned version only through `bunx` or `bun x`. Keep inline code out of what you pass to an interpreter, `python3 -c` for one. Keep `eval` out of every command.

### Processes

Start a long-running process with `run_in_background` set on the Bash call. Stop a process with `kill` and the PID it started under.

Keep `nohup`, a trailing `&`, and `disown` out of every command that backgrounds a process. Keep stopping processes by pattern, with `pkill` or `killall`, out of every command.

### Git state

Move a branch ref with `git reset --soft <sha>`. Restore a path to a commit's state with `git checkout <sha> -- <path>`. Set work aside with a temporary commit.

Keep `git reset --hard` out of every command. Keep a bare `git stash` and `git stash pop` out of every command.
