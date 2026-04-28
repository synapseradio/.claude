# Git & Commit

Applies when committing code or preparing a commit.

- Verify staged files with `git diff --cached --name-only` before committing. Never include planning artifacts (TASKS.md, TODO.md) unless explicitly requested.

## Git & Stack Workflow (when writing or modifying code)

- Use fork-based PR workflow (not direct push) for skill/shared branches.
- Use stax for stack operations; expect non-TTY workarounds may be needed. When rebasing with stax, you are expected to handle conflicts yourself. `-X ours`, autosquash.
