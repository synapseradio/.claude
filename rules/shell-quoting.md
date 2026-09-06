# Quoting in shell commands

This applies to every Bash tool call.

We value a command that runs as one piece. The shell is zsh, and an unquoted `!`, `?`, or glob character breaks a multi-line command mid-run. File content pushed through echo or a heredoc arrives altered, and Write and Edit carry it exactly.

```sudolang
quote = argument => match (argument) {
  case holds `!`, `?`, `*`, `[`, `]`, `$`, parentheses, or whitespace => single quotes
  case multi-line or special-character content => a heredoc with a quoted delimiter, <<'EOF'
}

require never nested double quotes
require file content never travels through echo or a heredoc into a file
```
