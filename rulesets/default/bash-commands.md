<!-- rule: bash-commands -->

## bash-commands

For every Bash tool call, optimize for a command the session's allow rules match part by part, running only the programs its text names, quoted so the shell reads it whole.

- fetch-and-run command: one that resolves a package from a registry and executes code from it in the same step, `npx` for one, `docker run` and `podman run` included

### The shape

Hold every part of a compound command as matched against the allow rules on its own, split at `&&`, `||`, `;`, `|`, `&`, and newlines. Give each call the fewest parts its step needs, two steps in one call only where they share shell state. Write every redirect target and every `tee` target as an absolute path, with a leading `~` kept out. Run git in another directory with `git -C <path> <subcommand>`, with `cd` kept out of every call that holds a git command.

### Quoting

Quote every command for zsh, the shell the Bash tool runs. Quote every variable expansion. Pass several arguments held in one variable as an array, `"${args[@]}"`. Single-quote an argument that holds `!`, `?`, `*`, `[`, `]`, `$`, parentheses, or whitespace. Put multi-line or special-character content in a heredoc with a quoted delimiter, `<<'EOF'`. Keep double quotes out of every double-quoted string.

### Programs

Run a repository's tools through the scripts its package.json defines.
A tool lacks a script ? call it at `node_modules/.bin/<tool>`.
A step needs a script of its own ? write it to a file in the scratchpad through Write, then run that file.
Run a shell with `-c` only to test how that shell behaves. Keep inline code out of what you pass to an interpreter, `python3 -c` for one. Keep `eval` out of every command.

Before every fetch-and-run call, state in the message the package, the version the command names, what it executes, and which installed tool falls short of the step.
The command is `bunx` or `bun x` ? run it on your own judgment, at a pinned version or `@latest` : run it only on the user's approval, at a pinned version.

### Processes

Stop a process with `kill` and the PID it started under, with `pkill` and `killall` kept out. Keep `nohup`, a trailing `&`, and `disown` out of every command that backgrounds a process.

### Git state

Move a branch ref with `git reset --soft <sha>`. Restore a path to a commit's state with `git checkout <sha> -- <path>`. Set work aside with a temporary commit. Keep `git reset --hard`, a bare `git stash`, and `git stash pop` out of every command.
