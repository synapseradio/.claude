<!-- rule: scratchpad -->

## scratchpad

For every temporary or working file you produce, an intermediate result, a throwaway script, generated data, a review, an audit, a plan, or a run file, optimize for a working file that lands where the next search finds it and stays out of every commit.

- `$repo`: the basename of the directory holding the path `git rev-parse --path-format=absolute --git-common-dir` prints, with a leading `.` written as `-`, `-claude` for `.claude`
- `$dir`: `$HOME/.scratchpad/$repo/$branch/` where `git branch --show-current` names a branch, and `$HOME/.scratchpad/$repo/` otherwise
- working file: `$dir/$slug__$hh-$mm$AMPM_$DD-$MM-$YYYY.md`, `condense-rules__02-45PM_20-09-2026.md` for one, timestamped at the first write

Write a working note at the moment you discover something important or new.
Get the path by running `$HOME/.claude/scripts/scratchpad-path.py $slug` from inside the repository, which reads the timestamp from the clock and creates the directory.
Plan mode holds ? keep working notes in the plan file until writing opens up.
A read-only mode holds ? skip setup.
Neither holds ? create the directory on first write and leave everything else as it stands.

place file
  | a temporary or working file inside a git repository
      = the working file, over any scratchpad or temp directory the harness names
  | a temporary or working file outside a git repository = the harness path exactly
  | a skill or workflow default such as `/tmp/<skill>-<slug>.md`
      = that file with that slug, saying once where it went
  | documentation the project ships = its docs tree
  | source = its source tree
  | a file the user named = where they named it
  | a fact worth keeping across sessions = a persistent store
  | unclear whether the output is a deliverable = ask

Keep every secret and credential out of `$HOME/.scratchpad/`. Treat avoiding the decision of where a real artifact lives as no ground for writing into `$HOME/.scratchpad/`.
