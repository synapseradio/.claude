# Git & Commit

Applies when committing code or preparing a commit.

- Verify staged files with `git diff --cached --name-only` before committing. Never include planning artifacts (TASKS.md, TODO.md) unless explicitly requested.
- **A pre-commit hook block is a failure, not a suggestion.** When a hook rejects the commit, the rejection is the next task: read the hook output, fix the underlying issue, re-stage, retry. Never use `--no-verify` to bypass it. Never `git commit --amend` over a hook-rejected attempt; create a new commit after the fix.

## Git & Branch Workflow (when writing or modifying code)

- Use fork-based PR workflow (not direct push) for skill/shared branches.
- Default to git directly for branch, commit, push, and rebase operations.
- Use worktrunk (`wt`) for worktree management.
- Use stax only when the user explicitly requests stacked branches or when continuing work on an existing stack. When rebasing with stax, handle conflicts yourself; `-X ours`, autosquash.
