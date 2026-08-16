GitCommit {
  Applies { committing, writing a commit message, moving between branches }

  Message {
    firstLine = "$type($scope): $description"
    type: feat | fix | docs | style | refactor | perf | test | build | ci
      | chore | revert, picked from what the diff does
    scope: optional, reused where the branch or repo already uses one
    description: imperative, lowercase start, no trailing period,
      identifiers in their real casing
    body: after one blank line, why the change happened
  }

  constraint RepoFormatWins {
    (the repo states a format: a commitlint, commitizen, or gitlint config,
      an enabled commit-msg hook, a documented convention, or a consistent
      branch history) => follow it exactly in place of Message
    (a hook is disabled, or its script is absent) => Message applies
    honor content bans, such as no URLs or co-author trailers, either way
  }

  constraint HooksStand {
    require you never pass `--no-verify`
    require you never amend a rejected attempt: fix the cause, commit anew
    (a hook rejects the commit) => make the rejection the next task
  }

  fn commit() {
    verify the staged set with `git diff --cached --name-only`, keeping
      planning artifacts out unless the user asks for them
      |> compose the message under RepoFormatWins |> commit
  }

  Branches {
    use the fork-based PR workflow on shared branches
    use separate worktrees for parallel work rather than switching in place
    (rebasing) => resolve conflicts with `-X ours` and autosquash by default
  }
}
