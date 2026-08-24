# Editing files

This applies always.

```sudolang
Constraints {
  require no stream editor ever modifies a file, whatever the hook catches:
    sed, gsed, awk, perl -i, any tool substituting in place from a pattern
    it never shows you
  use Edit or Write for every change, one-line substitutions and appended lines
    included, since each matches exactly and fails on a wrong match where a stream
    editor would mangle the rest of the file
  a stream editor serves only read-only inspection in a pipeline touching no file on disk
}

fn mechanicalBulkChange {
  write the script in a real language (Python, TypeScript, JavaScript, Ruby, or the like),
    matching exact strings, never loose patterns
  checkpoint first, git commit or git stash, so the script's whole effect stands
    as the only uncommitted diff
  require no checkpoint => do not run
  run |> report what changed |> read the diff |> run again, confirm it reports no change
}
```
