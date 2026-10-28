<!-- rule: exact-edits -->

## exact-edits

In every context and every turn, optimize for an edit that matches exactly and fails on a wrong match.

A stream editor is any tool substituting in place from a pattern whose matches stay out of your view, sed for one. Keep every file out of a stream editor's writes, whatever its name.

```haskell
edit
  | the work is read-only inspection in a pipeline that leaves every file on disk as it was
      = a stream editor may run
  | the change is mechanical across many sites = run a mechanical bulk change as below
  | otherwise = use Edit or Write, one-line substitutions and appended lines included
```

### A mechanical bulk change

Write the script in a real language, Python for one, matching exact strings in place of loose patterns. Make a checkpoint git commit, and run the script only after it. Report what changed, read the diff, and run again to confirm it reports zero changes.
