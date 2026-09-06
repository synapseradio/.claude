# Committing

This applies when committing, writing a commit message, or moving between branches.

We value a commit whose message says what the diff does and why, and whose hooks ran. A hook skipped with --no-verify leaves history the repo's own checks never accepted, and a rejected attempt amended hides the cause under a fresh attempt, so the cause gets fixed and the commit made anew. A planning artifact in the staged set reaches history nobody asked for.

```sudolang
Message {
  firstLine: "$type($scope): $description"
  type: feat | fix | docs | style | refactor | perf | test | build | ci | chore | revert,
    from what the diff does
  scope: optional, reused where the branch or repo already uses one
  description: imperative, starts lowercase, no trailing period, identifiers in their
    real casing
  body: after one blank line, why the change happened, for the decisions that were
    yours to make
}

format = repo => match (repo) {
  case it states a format through a commitlint, commitizen, or gitlint config, an enabled
    commit-msg hook, a documented convention, or a consistent branch history =>
    follow it exactly
  default => Message
}
honor the standing content bans either way: no URLs, no co-author trailers

fn commit() {
  verify the staged set with `git diff --cached --name-only`, planning artifacts out
    unless the user asks
  compose the message
  commit
  a hook rejects => make the rejection the next task
}

Branches {
  a branch other people push to or review => open the PR from your fork
  a parallel line of work => its own worktree
  rebasing => autosquash by default, conflicts resolved on their merits
}

require never pass --no-verify
require never amend a rejected attempt
```
