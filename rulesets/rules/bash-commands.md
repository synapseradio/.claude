## bash-commands

For every Bash tool call, optimize for a command the session's allow rules match part by part, running only the programs its text names, quoted so the shell reads it whole.

### The shape

Hold every part of a compound command as matched against the allow rules on its own, split at `&&`, `||`, `;`, `|`, `&`, and newlines. Give each call the fewest parts its step needs, two steps in one call only where they share shell state. Write every redirect target and every `tee` target as an absolute path, with a leading `~` kept out. Run git in another directory with `git -C <path> <subcommand>`, with `cd` kept out of every call that holds a git command.

### Output size

A command's output may exceed 20000 characters, a test suite's run for one ? redirect its stdout and stderr to a file at an absolute path in the scratchpad -> scan that file with grep, jq, ast-grep, or a Read by line range, each scan's output bounded within 20000 characters.
Keep every Bash response over 20000 characters out of context.

### Quoting

Quote every command for zsh, the shell the Bash tool runs. Quote every variable expansion. Pass several arguments held in one variable as an array, `"${args[@]}"`. Single-quote an argument that holds `!`, `?`, `*`, `[`, `]`, `$`, parentheses, or whitespace. Put multi-line or special-character content in a heredoc with a quoted delimiter, `<<'EOF'`. Keep double quotes out of every double-quoted string.

### Programs

Run a repository's tools through the scripts its package.json defines.
A tool lacks a script ? call it at `node_modules/.bin/<tool>`.
A step needs a script of its own ? write it to a file in the scratchpad through Write, then run that file.
Keep inline code out of what you pass to an interpreter, `python3 -c` for one.
Run a generator that writes its checkout's paths or content into files outside that checkout only from the canonical checkout, once the branch merges, with every worktree kept out -> before it writes, check each target repository for an in-progress rebase or conflict.

### Processes

Stop a process with `kill` and the PID it started under, with `pkill` and `killall` kept out. Keep `nohup`, a trailing `&`, and `disown` out of every command that backgrounds a process.

### Git state

Move a branch ref with `git reset --soft <sha>`. Restore a path to a commit's state with `git checkout <sha> -- <path>`. Set work aside with a temporary commit. Keep a bare `git stash` and `git stash pop` out of every command.
Run a test suite against each commit of a branch in a plain shell, looping over `git checkout --detach <sha>` with `GIT_DIR` and `GIT_WORK_TREE` unset, with every test run kept out of `git rebase --exec`.
