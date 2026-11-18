## bash-commands

For every Bash tool call, optimize for a command the session's allow rules match part by part, running only the programs its text names and quoted so the shell reads it whole.

### The shape

Hold every part of a compound command as matched against the allow rules on its own, split at each of `&&` `||` `;` `|` `&` and at newlines.
Give each call the fewest parts its step needs, two steps in one call only where they share shell state.
Write every redirect and `tee` target as an absolute path, rooted at `"$HOME"` under the home directory and at `/` elsewhere, with a leading `~` kept out.
Run git in another directory with `git -C <path> <subcommand>`, with `cd` kept out of every call that holds a git command.

### Output size

output
  | it may exceed 5000 characters, such as a test suite's run = redirect stdout and stderr to a file at an absolute scratchpad path -> scan that file with a search tool or a Read by line range, each scan's output within 5000 characters

Keep every Bash response over 5000 characters out of context.

### Quoting

Quote every command for zsh, the shell the Bash tool runs.
Quote every variable expansion.
Pass several arguments held in one variable as an array, `"${args[@]}"`.
Single-quote an argument that holds whitespace or parentheses or any of `!` `?` `*` `[` `]` `$`.
Put multi-line or special-character content in a heredoc with a quoted delimiter, `<<'EOF'`.
Keep double quotes out of every double-quoted string.

### Programs

Run a repository's tools through the scripts its package.json defines.

program
  | a tool lacks a script = run the repository's installed copy through its package manager in the form that manager takes, such as `bun <tool>`
  | a step needs a script of its own = write it to a scratchpad file through Write -> run that file

Keep inline code out of what you pass to an interpreter, such as `python3 -c`.
Run a generator that writes its checkout's paths or content into files outside that checkout only from the canonical checkout once the branch merges, with every worktree kept out -> before it writes, check each target repository for an in-progress rebase or conflict.

### Processes

Stop a process with `kill` and the PID it started under, with `pkill` and `killall` kept out.
Keep `nohup`, a trailing `&`, and `disown` out of every command that backgrounds a process.

### Git state

Move a branch ref with `git reset --soft <sha>` only as a command's first step, on a branch other than the default, over commits no remote-tracking ref reaches.
Restore a path to a commit's state with `git checkout <sha> -- <path>`.
Set work aside with a temporary commit.
Keep a bare `git stash` and `git stash pop` out of every command.
