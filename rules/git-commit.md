# Git & Commit

Applies when committing code or preparing a commit.

- Verify staged files with `git diff --cached --name-only` before committing. Never include planning artifacts unless explicitly requested.
- **A pre-commit hook block is a failure, not a suggestion.** When a hook rejects the commit, the rejection is the next task. Never use `--no-verify` to bypass it. After a hook rejects a commit, never amend the rejected attempt. Create a new commit after the fix.

## Git & Branch Workflow

Applies when writing or modifying code.

- Use the fork-based PR workflow on shared branches.
- Default to git for routine operations.
- Use worktrunk (`wt`) for worktree management.
- When rebasing, default to `-X ours` and autosquash to resolve conflicts deterministically.
