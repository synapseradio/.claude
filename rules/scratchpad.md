# Where temporary files go

This applies to any temporary or working file: intermediate results, throwaway scripts, generated data, reviews, audits, plans, run files.

We value a working file that lands where the next search finds it and never reaches a commit. The global gitignore at `~/.dotfiles/git/ignore` covers scratchpad/, so creating the directory needs no other change, and the same ignore drops everything here from every clone, so a fact worth keeping across sessions goes to a persistent store. A real artifact written here to dodge a decision about its home loses its home.

```sudolang
dir = if (`git branch --show-current` names a branch) "scratchpad/$branch/" else "scratchpad/",
  at the root of the repository in play
file = "$dir/$slug__$DD-MM-YY-HHmm.md", timestamped at the first write

route = output => match (output) {
  case a temporary or working file inside a git repository => file, whatever path the
    harness names as scratchpad or temp directory
  case a temporary or working file outside a git repository => the harness path exactly
  case a skill or workflow default such as /tmp/<skill>-<slug>.md => file with that slug,
    say once where it went
  case documentation the project ships => its docs tree
  case source => its source tree
  case a file the user named => where they named it
  case a fact worth keeping across sessions => a persistent store
  case unclear whether a deliverable => ask
}

setup = session => match (session) {
  case plan mode holds => working notes stay in the plan file until writing opens up
  case a read-only mode holds => skip setup
  default => create the directory on first write, change nothing else
}

require no secret or credential lands in scratchpad/
require never write into scratchpad/ to avoid deciding where a real artifact lives
```
