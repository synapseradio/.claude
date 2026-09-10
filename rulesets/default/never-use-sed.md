<!-- rule: never-use-sed -->

## never-use-sed

In every context and every turn, optimize for an edit that matches exactly and fails on a wrong match.

A stream editor is any tool substituting in place from a pattern it never shows you, sed for one. Never let a stream editor modify a file, whatever its name.

Where the work is read-only inspection in a pipeline touching no file on disk, a stream editor may run. Where the change is mechanical across many sites, run a mechanical bulk change as below. Otherwise, use Edit or Write, one-line substitutions and appended lines included.

### A mechanical bulk change

Write the script in a real language, Python for one, matching exact strings, never loose patterns. Checkpoint first, with a git commit or a git stash. Where no checkpoint was made, do not run. Then run, report what changed, read the diff, and run again to confirm it reports no change.
