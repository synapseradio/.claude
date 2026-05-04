# Git & Commit

Applies when committing code or preparing a commit.

- Verify staged files with `git diff --cached --name-only` before committing. Never include planning artifacts (TASKS.md, TODO.md) unless explicitly requested.
- **A red suite blocks the commit.** Before `git commit` (and before any "ready to commit?" claim to the user), every deterministic check on the changed code must be green: tests, lint, pre-commit hooks, build. If any are red, the failures become the next tasks via `TaskCreate` and are fixed first — see Core Rule 12 and `testing.md` "When tests fail". Do not commit on red. Do not ask the user to weigh deferral as a default move.
- **A pre-commit hook block is a failure, not a suggestion.** When a hook rejects the commit, the rejection is the next task: read the hook output, fix the underlying issue, re-stage, retry. Never use `--no-verify` to bypass it. Never `git commit --amend` over a hook-rejected attempt; create a new commit after the fix.

## Git & Stack Workflow (when writing or modifying code)

- Use fork-based PR workflow (not direct push) for skill/shared branches.
- Use stax for stack operations; expect non-TTY workarounds may be needed. When rebasing with stax, you are expected to handle conflicts yourself. `-X ours`, autosquash.
