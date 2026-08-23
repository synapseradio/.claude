# Editing files

This applies always.

No stream editor ever modifies a file, whatever the hook catches. Stream editors include sed, gsed, awk, `perl -i`, and any tool substituting in place from a pattern it never shows you. Use Edit or Write for every change, a one-line substitution and an appended line included, since each matches exactly and fails on a wrong match where a stream editor would mangle the rest of the file. Use a stream editor only for read-only inspection in a pipeline that touches no file on disk.

When a change repeats mechanically across many files or lines, write the script in a real language (Python, TypeScript, JavaScript, Ruby, or the like), matching exact strings and never loose patterns. Take a checkpoint before it runs, `git commit` or `git stash`, so the script's whole effect stands as the only uncommitted diff. Without a checkpoint, do not run the script. Checkpoint, run, report what changed, read the diff, then run again and confirm it reports no change.
