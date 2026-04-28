# How to work with me

Global instructions governing behavior across all projects.

Detailed rules live in `~/.claude/rules/` (loaded by Claude Code, with path scoping where applicable). Pointer-only references — read them when a rule says to — live in `~/.claude/references/`.

## Index

### Always-loaded rules (`~/.claude/rules/`)

- [core-rules.md](./rules/core-rules.md) — the 12 numbered Core Rules
- [operating-rules.md](./rules/operating-rules.md) — non-negotiable Rules of Operation (tasks, plan-mode, conflicts, subagents, secrets, posting on user's behalf)
- [reasoning-principles.md](./rules/reasoning-principles.md) — how to think (probabilistic beliefs, disconfirmation, calibration)
- [persistent-memory.md](./rules/persistent-memory.md) — when and where to save memory across sessions
- [search-tools.md](./rules/search-tools.md) — web search etiquette
- [git-commit.md](./rules/git-commit.md) — pre-commit checks and stack workflow
- [debugging.md](./rules/debugging.md) — investigate the user's identified root cause
- [audit-explore.md](./rules/audit-explore.md) — cast a wide net before reporting
- [testing.md](./rules/testing.md) — test-run scope, isolation, mocks, names, assertions
- [progressive-enhancement.md](./rules/progressive-enhancement.md) — baseline prose first; structure (headers/tables/lists) is enhancement

### Path-scoped rules (`~/.claude/rules/`, load when matching files are touched)

- [code-write.md](./rules/code-write.md) — writing or modifying source code
- [code-implement.md](./rules/code-implement.md) — TDD scientific-method workflow
- [evergreen-prose.md](./rules/evergreen-prose.md) — no transitional framing in evergreen artifacts
- [writing-for-humans.md](./rules/writing-for-humans.md) — prose voice and clarity
- [bash-style-guide.md](./rules/bash-style-guide.md) — Google Shell Style Guide (shell, bash, zsh, bats)

### References (`~/.claude/references/`, read on demand)

- [decompose-reference.md](./references/decompose-reference.md) — decomposition method (cited by Core Rule 1)
- [evaluative-language.md](./references/evaluative-language.md) — five-predicate harness for judgment words (cited by Core Rules 8 and 11)
