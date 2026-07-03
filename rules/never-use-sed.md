<system-reminder>
# Never Use sed for Edits

Applies whenever you change the contents of a file.

Never use `sed`, `gsed`, `awk`, `perl -i`, or any other stream editor to modify a file. Use the `Edit` and `Write` tools instead. They match exactly, fail loudly when the match is wrong, and never silently mangle the rest of the file.

This holds even for edits that look trivial in a stream editor: a one-line substitution, an in-place delete, appending a line. Reach for `Edit`/`Write` every time.

`sed`/`awk` are fine for read-only inspection in a pipeline, where they touch no file on disk. The ban is on using them to write.
</system-reminder>
