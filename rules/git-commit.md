# Git & Commit

```sudolang
GitCommit {
  Applies { git work: committing, writing a commit message,
            moving between branches }

  Committing {
    verify staged files with `git diff --cached --name-only` before committing
    planning artifacts -> never included, unless explicitly requested
    HookBlock {
      a pre-commit hook block = a failure, not a suggestion
      hook rejects the commit -> the rejection becomes the next task
      never `--no-verify` to bypass it
      after a rejection -> never amend the rejected attempt;
        fix the cause and create a new commit
    }
  }

  MessageFormat {
    first line = `type(scope): description`  // the commitizen convention
    type  { feat | fix | docs | style | refactor | perf | test
          | build | ci | chore | revert
          // picked by what the change does, judged from its diff,
          // never from the wording of a task
    }
    scope { optional
            branch or repo already establishes one (a ticket id, a package
              name, an area) -> reuse it for consistency across the branch }
    description { an imperative; starts lowercase; no trailing period
                  proper nouns and identifiers keep their real casing }
    longer explanation -> the body, after one blank line
      // why the change happened, and what matters when changing it later
  }

  DeterminismWins {
    // repo tools, generally deterministic, win as a general concept:
    // they are our tools; the commit format is one instance
    the repository states a format -> follow it instead of the default above
    StatesAFormat = [
      a commit linter or generator config: commitlint, commitizen,
        `.czrc`, `.cz.*`, `.commitlintrc*`, gitlint, or an equivalent,
      an enabled commit-msg hook that checks message format,
      a documented convention in CONTRIBUTING, the docs tree, or a rules file,
      a clear, consistent format already in the branch's own history,
    ]
    match it exactly: type list, scope rules, casing
    a disabled hook | a referenced-but-absent script -> states no format;
      the default above returns
    content bans (no company names, no URLs, no co-author trailers, and the
      like) -> honored regardless of format
  }

  BranchWorkflow {
    shared branches -> the fork-based PR workflow
    routine operations -> default to git
    parallel lines of work -> separate worktrees, rather than switching
      branches in place
    rebasing -> default to `-X ours` and autosquash
      // so conflicts resolve deterministically
  }
}
```
