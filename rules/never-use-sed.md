# Editing files

This applies always.

We value an edit that matches exactly and fails on a wrong match. A stream editor substitutes from a pattern it never shows you and mangles the rest of the file on a wrong match, where Edit and Write fail. A bulk script run without a checkpoint leaves no diff that shows its whole effect.

```sudolang
edit = change => match (change) {
  case read-only inspection in a pipeline touching no file on disk => a stream editor may run
  case a mechanical change across many sites => mechanicalBulkChange
  default => Edit or Write, one-line substitutions and appended lines included
}

fn mechanicalBulkChange() {
  write the script in a real language, Python, TypeScript, JavaScript, Ruby, or the like,
    matching exact strings, never loose patterns
  checkpoint first, a git commit or a git stash, so the script's whole effect stands as
    the only uncommitted diff
  no checkpoint made => do not run
  run |> report what changed |> read the diff |> run again, confirm it reports no change
}

require no stream editor ever modifies a file, whatever the hook catches: sed, gsed, awk,
  perl -i, any tool substituting in place from a pattern it never shows you
```
