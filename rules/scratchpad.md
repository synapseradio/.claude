# Where temporary files go

This applies to any temporary or working file: intermediate results, throwaway scripts, generated data, reviews, audits, plans, run files.

```sudolang
dir = if (`git branch --show-current` names a branch) "scratchpad/$branch/"
  else "scratchpad/", at the root of the repository in play
file = "$dir/$slug__$DD-MM-YY-HHmm.md", timestamped at the first write

Constraints {
  inside a git repository, every path the harness gives as scratchpad or temp
    directory names this directory; outside one, use the harness path exactly
  a skill or workflow names a default such as /tmp/<skill>-<slug>.md =>
    write it at the layout path with that slug, say once where it went
  create the directory on first write and change nothing else,
    since the global gitignore at ~/.dotfiles/git/ignore covers scratchpad/
  plan mode holds => working notes stay in the plan file until writing opens up
  a read-only mode holds => skip setup
  documentation the project ships goes to its docs tree, source to its source tree,
    a file the user named to where they named it
  require no secret or credential lands in scratchpad/
  never write into scratchpad/ to avoid deciding where a real artifact lives
  a fact worth keeping across sessions => store it as a persistent memory
  unclear whether output is a deliverable => ask
}
```
