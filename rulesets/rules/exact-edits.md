<!-- rule: exact-edits -->

## exact-edits

In every context and every turn, optimize for an edit that matches exactly and fails on a wrong match.

- stream editor: any tool substituting in place from a pattern whose matches stay out of your view, sed for one

Keep every file out of a stream editor's writes, whatever its name.

edit
  | the work is read-only inspection in a pipeline that leaves every file on disk as it was
      = a stream editor may run
  | the change is mechanical across many sites
      = write a script in a real language, Python for one, matching exact strings in place of loose patterns -> make a checkpoint git commit -> run the script -> report what changed -> read the diff -> run again to confirm it reports zero changes
  | otherwise = use Edit or Write, one-line substitutions and appended lines included
