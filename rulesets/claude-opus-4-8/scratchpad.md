<!-- rule: scratchpad -->

## scratchpad

This rule applies when you are producing a temporary or working file: an intermediate result, a throwaway script, generated data, a review, an audit, a plan, a run file. Optimize for a working file that lands where the next search finds it and never reaches a commit.

A working file saves context and keeps a long conversation alive as it grows, holding what the context window drops. A slug with a timestamp is what the next search finds. The global gitignore at `~/.dotfiles/git/ignore` covers scratchpad/, so creating the directory needs no other change. The same ignore drops everything here from every clone. A real artifact written here while its home stands undecided loses that home with it.

### The location

The directory is `scratchpad/$branch/` where `git branch --show-current` names a branch, and `scratchpad/` otherwise, at the root of the repository in play. The file is `$dir/$slug__$DD-MM-YY-HHmm.md`, timestamped at the first write.

Where plan mode holds, working notes stay in the plan file until writing opens up. Where a read-only mode holds, skip setup. Otherwise, create the directory on first write and change nothing else.

### Where each file goes

- A temporary or working file inside a git repository goes to that file, whatever path the harness names as scratchpad or temp directory.
- A temporary or working file outside a git repository goes to the harness path exactly.
- A skill or workflow default such as `/tmp/<skill>-<slug>.md` goes to that file with that slug. Say once where it went.
- Documentation the project ships goes to its docs tree.
- Source goes to its source tree.
- A file the user named goes where they named it.
- A fact worth keeping across sessions goes to a persistent store.
- Where it is unclear whether the output is a deliverable, ask.

Never let a secret or credential land in scratchpad/. Never write into scratchpad/ to avoid deciding where a real artifact lives.
