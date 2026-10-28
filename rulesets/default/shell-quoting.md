<!-- rule: shell-quoting -->

## shell-quoting

For every Bash tool call, optimize for a command that runs as one piece, quoted so the shell reads it whole.

Quote every command for zsh, the shell the Bash tool runs. Quote every variable expansion. Pass several arguments held in one variable as an array, `"${args[@]}"`. Single-quote an argument that holds `!`, `?`, `*`, `[`, `]`, `$`, parentheses, or whitespace. Put multi-line or special-character content in a heredoc with a quoted delimiter, `<<'EOF'`. Keep double quotes out of every double-quoted string.
