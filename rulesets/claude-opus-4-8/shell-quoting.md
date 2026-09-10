<!-- rule: shell-quoting -->

## shell-quoting

When you are making a Bash tool call, optimize for a command that runs as one piece, quoted so the shell reads it whole.

A command that runs whole leaves a record of what ran that can be trusted as it stands. The shell is zsh, where an unquoted `!`, `?`, or glob character breaks a multi-line command mid-run. File content pushed through echo or a heredoc can arrive altered, and Write and Edit carry it exactly.

Single-quote an argument that holds `!`, `?`, `*`, `[`, `]`, `$`, parentheses, or whitespace. Put multi-line or special-character content in a heredoc with a quoted delimiter, `<<'EOF'`. Never nest double quotes. Carry file content into a file through Write or Edit only.
