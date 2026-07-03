# graphify reference

Companion to [../rules/graphify.md](../rules/graphify.md). Read this when the rule has cued graphify work and you need layout, save-result mechanics, the SKILL override, or recovery procedure.

## Layout

- Per-repo graph: `~/.graphify/local/<rel-path>/graphify-out/graph.json`, where `<rel-path>` means the source path with `$HOME/` stripped. Never inside the source repo.
- Supergraph: `~/.graphify/super-graph.json`.

## Refreshing the graph in detail

`lodestar` lives at `~/.dotfiles/tools/lodestar/bin/lodestar`, reaching PATH through the `tools/*/bin` glob in `shell/profile`. Idempotent, transactional, preserves uncommitted state.

- `lodestar sync -a` — sweep all in-scope repos. Bare `lodestar` prints help and does not mutate.
- `lodestar sync <name>` — sync one repo (clones first if it matches an in-scope GH repo and isn't local).
- `lodestar bulk <owner> [-n N]` — clone and graph the top `N` most-active repos for an owner (default 40, most-recent push first), then merge once. Concurrency comes from `LODESTAR_JOBS` or `-J N` (default 8); sweep and bulk both run parallel by default.
- `lodestar add <path|owner/name|url>` / `lodestar remove <name>` / `lodestar prune` / `lodestar viz [<name>]`.

A `UserPromptSubmit` hook fires `lodestar sync <name>` in the background when a prompt names an in-scope or registered repo (1h cooldown). Each in-scope repo also has post-commit / post-checkout hooks plus a merge driver for `graph.json`.

## SKILL override

The SKILL at `~/.claude/skills/graphify/SKILL.md` works cwd-relative and assumes `./graphify-out/`. On this machine, graphs live under `~/.graphify/local/<rel-path>/`. Translate every cwd-relative path the SKILL uses by rooting it at `~/.graphify/local/<rel-path>/`. For `cd <repo> && graphify extract|update`, use `lodestar sync <name>` instead.

Never `cd` into a source repo to run `graphify` — it writes into the source tree. Never read or write to `<source-repo>/graphify-out/`.

## Save load-bearing answers

```bash
graphify save-result --question "<q>" --answer "<a>" --type query --nodes <n1> <n2> \
  --memory-dir ~/.graphify/local/<rel-path>/graphify-out/memory
```

Use `--type path_query` for `path` results, `--type explain` for `explain`.

## Forced-reset recovery

If `lodestar` finds local trunk diverged from `origin/<trunk>`, it tags `lodestar/pre-reset/<sha>/<utc-timestamp>` before resetting. Recover with `git reset --hard <tag>`.
