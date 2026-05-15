# graphify reference

Companion to [../rules/graphify.md](../rules/graphify.md). Read this when the rule has cued graphify work and you need layout, save-result mechanics, the SKILL override, or recovery procedure.

## Layout

- Per-repo graph: `~/.graphify/local/<rel-path>/graphify-out/graph.json`, where `<rel-path>` is the source path with `$HOME/` stripped. Never inside the source repo.
- Supergraph: `~/.graphify/super-graph.json`.

## Refreshing the graph in detail

`grip` is `~/.graphify/sync.sh` on PATH. Idempotent, transactional, preserves uncommitted state.

- `grip` — sweep all in-scope repos plus extras.
- `grip <name>` — sync one repo (clones first if it matches an in-scope GH repo and isn't local).
- `grip add <path|owner/name|url>` / `grip remove <name>` / `grip prune` / `grip viz [<name>]`.

A `UserPromptSubmit` hook fires `grip <name>` in the background when a prompt names an in-scope or extras repo (1h cooldown). Each in-scope repo also has post-commit / post-checkout hooks plus a merge driver for `graph.json`.

## SKILL override

The SKILL at `~/.claude/skills/graphify/SKILL.md` is cwd-relative and assumes `./graphify-out/`. On this machine, graphs live under `~/.graphify/local/<rel-path>/`. Translate every cwd-relative path the SKILL uses by rooting it at `~/.graphify/local/<rel-path>/`. For `cd <repo> && graphify extract|update`, use `grip <name>` instead.

Never `cd` into a source repo to run `graphify` — it writes into the source tree. Never read or write to `<source-repo>/graphify-out/`.

## Save load-bearing answers

```bash
graphify save-result --question "<q>" --answer "<a>" --type query --nodes <n1> <n2> \
  --memory-dir ~/.graphify/local/<rel-path>/graphify-out/memory
```

Use `--type path_query` for `path` results, `--type explain` for `explain`.

## Forced-reset recovery

If `grip` finds local trunk diverged from `origin/<trunk>`, it tags `grip/pre-reset/<sha>/<utc-timestamp>` before resetting. Recover with `git reset --hard <tag>`.
