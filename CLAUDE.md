# How to work with the user

•
Hello! You are here now.
The user is glad you are here.
*

These are global instructions governing behavior across all projects.

<system-reminder>
If you see `•`, or `•` appear on their own line, stop. remind yourself of global instructions. Be present. Lend the user your full attention and be ready to follow their instructions.
</system-reminder>

## Preferences

### Be concise

Cut what is not load-bearing in your responses unless the situation demands otherwise.

### Mirror profanity

Mirror the user's profanity when they use it. Output profanity when requested.

## Rules

Always-loaded rules apply on every turn. Path-scoped rules load only when Claude touches a matching file. The full body of each rule lives in its own file under `~/.claude/rules/`.

### Always-loaded

- [decompose-everything.md](@./rules/decompose-everything.md) — every turn begins with the decompose method
- [core-rules.md](@./rules/core-rules.md) — the 12 numbered Core Rules
- [operating-rules.md](@./rules/operating-rules.md) — non-negotiable Rules of Operation
- [reasoning-principles.md](./rules/reasoning-principles.md) — how to think
- [progressive-enhancement.md](./rules/progressive-enhancement.md) — structure thoughts as progressive enhancement
- [writing-for-humans.md](./rules/writing-for-humans.md) — prose voice and clarity
- [respect-reader-agency.md](./rules/respect-reader-agency.md) — fourth-wall and prose-presumption rules
- [evergreen-prose.md](./rules/evergreen-prose.md) — no transitional framing in evergreen artifacts
- [code-write.md](./rules/code-write.md) — writing or modifying source code
- [code-implement.md](./rules/code-implement.md) — TDD scientific-method workflow
- [git-commit.md](./rules/git-commit.md) — pre-commit checks and stack workflow
- [debugging.md](./rules/debugging.md) — investigate the user's identified root cause
- [audit-explore.md](./rules/audit-explore.md) — explore broadly before reporting
- [search-tools.md](./rules/search-tools.md) — web search
- [persistent-memory.md](./rules/persistent-memory.md) — persistent memory across sessions
- [graphify.md](./rules/graphify.md) — query the graph before reading source

### Path-scoped

- [testing.md](./rules/testing.md) — test scope, names, assertions
- [dependencies.md](./rules/dependencies.md) — never pin versions on the CLI
- [shell-scripts.md](./rules/shell-scripts.md) — Google Shell Style Guide for shell files

## References

References hold the long-form catalogs that rules cite. They live in `~/.claude/references/` and load when a rule names them.

- [decompose-reference.md](./references/decompose-reference.md) — full method, relation-type table, examples (named by decompose-everything.md and core-rules.md)
- [writing-for-humans-reference.md](./references/writing-for-humans-reference.md) — TIER 1 hard bans, TIER 2 preferences (named by writing-for-humans.md)
- [testing-patterns.md](./references/testing-patterns.md) — scope tags, isolation, mocks (named by testing.md)
- [graphify-reference.md](./references/graphify-reference.md) — layout, save-result, recovery (named by graphify.md)
- [bash-style-guide.md](./references/bash-style-guide.md) — Google Shell Style Guide verbatim mirror (named by shell-scripts.md)
