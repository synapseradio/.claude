# Committing

This applies when committing, writing a commit message, or moving between branches.

```sudolang
firstLine = "$type($scope): $description"
type: feat | fix | docs | style | refactor | perf | test | build | ci | chore | revert,
  from what the diff does
scope: optional, reused where the branch or repo already uses one
description: imperative, starts lowercase, no trailing period,
  identifiers in their real casing
body: after one blank line, why the change happened

format = match {
  the repo states one (commitlint, commitizen, or gitlint config, an enabled
    commit-msg hook, a documented convention, a consistent branch history) =>
    follow it exactly
  a hook disabled or its script absent => the format above
}
honor content bans either way, such as no URLs or no co-author trailers

Constraints {
  hooks stand: never pass --no-verify
  never amend a rejected attempt: fix the cause, commit anew
  a hook rejects => make the rejection the next task
}

fn commit {
  verify the staged set with `git diff --cached --name-only`,
    planning artifacts out unless the user asks
  compose the message
  commit
}

use the fork-based PR workflow on shared branches
use separate worktrees for parallel work instead of switching branches in one checkout
rebasing => resolve conflicts with -X ours and autosquash by default
```
