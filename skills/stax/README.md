# stax

Agent Skill for [stax](https://github.com/cesarferreira/stax) (v0.27.0) — a fast Rust CLI for stacked Git branches and PRs. When loaded, agents default to stax over raw git for all branch, rebase, push, and PR operations that stax can handle.

## Install

```sh
# From local path
claude skill add --path ~/.claude/skills/stax

# Or copy the stax/ directory into your project's .claude/skills/
```

## What it does

- Routes all common git branch/rebase/push/PR operations through stax equivalents
- Provides a git fallback table for operations stax doesn't cover (selective staging, stash, blame, cherry-pick, tags)
- Ensures agent-safe invocation with `--yes --no-prompt --quiet` flags
- Includes 12+ composable workflows for stacked development

## References

| File | Purpose |
|------|---------|
| `references/commands.md` | Complete command reference — every command, every flag |
| `references/workflows.md` | 12+ composable step-by-step workflows |
| `references/concepts.md` | Mental model: stacks, trunk, parent/child, risk classification |
| `references/stax-first.md` | Exhaustive git-to-stax operation mapping |

## Usage

The skill activates automatically when agents encounter git branch, rebase, push, or PR operations. Key patterns:

```sh
# Create a stacked branch
stax create feature-name -m "Add feature"

# Stage all changes and amend
stax modify

# Submit stack for review
stax submit --yes --no-prompt

# Sync, restack, and submit
stax cascade

# Merge the stack
stax merge --yes --when-ready
```

## Prerequisites

- stax v0.27.0+ installed (`cargo install stax` or via release binary)
- GitHub authentication configured (`stax auth`)

## License

MIT
