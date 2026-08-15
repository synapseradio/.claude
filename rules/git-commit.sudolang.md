# Git & Commit

Commit work runs on verified staging, the commitizen message convention, and
whatever format the repository's own tooling states, which wins wherever it
exists. Branch work prefers separate worktrees over switching branches in
place, and a hook that rejects a commit sets the next task.

GitCommit {
  Applies { git work: committing, writing a commit message,
            moving between branches }

  fn commit() {
    verifyStaged(`git diff --cached --name-only`)
      |> composeMessage under DeterminismWins
      |> commit
    (a hook rejects the commit, a pre-commit block included) => the rejection
      becomes the next task
  }

  Constraints {
    planning artifacts stay out of the commit, unless the user explicitly
      asks for them
  }
  require you never bypass a hook with `--no-verify`
  require you never amend a rejected attempt: fix the cause and create
    a new commit

  MessageFormat {
    first line = `type(scope): description`, the commitizen convention
    type  { feat | fix | docs | style | refactor | perf | test
          | build | ci | chore | revert
          pick the type from what the diff shows the change does, never from
            the wording of a task
    }
    scope { optional. when the branch or the repo already establishes one,
            a ticket id, a package name, or an area, reuse it for
            consistency across the branch }
    description { an imperative that starts lowercase and carries no
                  trailing period. proper nouns and identifiers keep their
                  real casing }
    put a longer explanation in the body, after one blank line, saying why
      the change happened and what matters when changing it later
  }

  DeterminismWins {
    (the repository states a format) =>
      follow it instead of MessageFormat, exactly: type list, scope
      rules, casing
    StatesAFormat = [
      a commit linter or generator config: commitlint, commitizen,
        `.czrc`, `.cz.*`, `.commitlintrc*`, gitlint, or an equivalent,
      an enabled commit-msg hook that checks message format,
      a documented convention in CONTRIBUTING, the docs tree, or a rules file,
      a clear, consistent format already in the branch's own history,
    ]
    Constraints {
      a disabled hook, or a script referenced but absent, states no format,
        and MessageFormat returns
      content bans (no company names, no URLs, no co-author trailers, and
        the like) are honored regardless of format
    }
  }

  BranchWorkflow {
    Constraints {
      on shared branches, use the fork-based PR workflow
      for routine operations, default to git
      for parallel lines of work, use separate worktrees rather than
        switching branches in place
      when rebasing, resolve conflicts deterministically with `-X ours` and
        autosquash by default
    }
  }
}
