# Quoting in shell commands

This applies to every Bash tool call, since the shell is zsh and an unquoted `!`, `?`, or glob character breaks a multi-line command mid-run.

```sudolang
Constraints {
  single-quote every argument holding !, ?, *, [, ], $, parentheses, or whitespace
  multi-line or special-character content => a heredoc with a quoted delimiter
    (<<'EOF'), never nested double quotes
  file content never travels through echo or a heredoc into a file:
    Write and Edit carry it exactly
}
```
