# Where temporary files go

This applies to any temporary or working file: intermediate results, throwaway scripts, generated data, reviews, audits, plans, run files.

The root sits at `scratchpad/` at the root of the repository in play. When `git branch --show-current` names a branch, the directory is `scratchpad/$branch/`, and otherwise the root itself. A file lands at `$dir/$slug__$DD-MM-YY-HHmm.md`, timestamped at the first write.

Inside a git repository, read every path the harness gives as its scratchpad or temp directory as naming that directory, and write there. Outside a git repository, use the harness path exactly as given. When a skill or workflow names a default such as `/tmp/<skill>-<slug>.md`, write it at the layout path with that slug, and say once where it went.

Create the directory on first write and change nothing else, since the global gitignore at `~/.dotfiles/git/ignore` covers `scratchpad/`. While plan mode holds, keep working notes in the plan file until writing opens up. While a read-only mode holds, skip setup.

Documentation the project ships goes to its docs tree, source to its source tree, and a file the user named to where they named it. No secret or credential lands in `scratchpad/`. Never write into `scratchpad/` to avoid deciding where a real artifact lives. When a fact is worth keeping across sessions, store it as a persistent memory. When you cannot tell whether output is a deliverable, ask.
