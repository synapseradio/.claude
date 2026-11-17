## scratchpad

For every temporary or working file you produce, a review or a plan included, optimize for a working file that lands where the next search finds it and stays out of every commit.

- `$repo`: the basename of the directory holding the path `git rev-parse --path-format=absolute --git-common-dir` prints, with a leading `.` written as `-`, `-claude` for `.claude`
- `$dir`: `$HOME/.scratchpad/$repo/$branch/` where `git branch --show-current` names a branch, and `$HOME/.scratchpad/$repo/` otherwise
- working file: `$dir/$slug__$hh-$mm$AMPM_$DD-$MM-$YYYY.md` such as `condense-rules__02-45PM_20-09-2026.md`, timestamped at the first write

Write a working note at the moment you discover something important or new.
Get the path by running `~/.claude/scripts/scratchpad-path.py $slug` from inside the repository, which reads the timestamp from the clock and creates the directory.

mode
  | plan mode holds = keep working notes in the plan file until writing opens up
  | a read-only mode holds = skip setup
  | otherwise = create the directory on first write and leave everything else as it stands

place file
  | an ephemeral log or command output that no later step reads = a file under `/tmp`
  | a temporary or working file inside a git repository = the working file, over any scratchpad or temp directory the harness names
  | a temporary or working file outside a git repository = the harness path exactly
  | a skill or workflow default such as `/tmp/<skill>-<slug>.md` = that file with that slug, saying once where it went
  | documentation the project ships = its docs tree
  | source = its source tree
  | a file the user named = where they named it
  | a fact worth keeping across sessions = a persistent store
  | unclear whether the output is a deliverable = ask

Keep every secret and credential out of `$HOME/.scratchpad/`.
Treat avoiding the decision of where a real artifact lives as no ground for writing into `$HOME/.scratchpad/`.
