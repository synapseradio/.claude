# graphify

When the user invokes graphify, references a repo under `~/projects/`, or runs graphify commands.

## Layout

- Per-repo graph: `~/.graphify/local/<rel-path>/graphify-out/graph.json`, where `<rel-path>` is the source path with `$HOME/` stripped. Never inside the source repo.
- Supergraph: `~/.graphify/super-graph.json`.

## Refreshing the graph

`grip` is `~/.graphify/sync.sh` on PATH. Idempotent, transactional, preserves uncommitted state.

- `grip` — sweep all in-scope repos plus extras.
- `grip <name>` — sync one repo (clones first if it matches an in-scope GH repo and isn't local).
- `grip add <path|owner/name|url>` / `grip remove <name>` / `grip prune` / `grip viz [<name>]`.

A `UserPromptSubmit` hook fires `grip <name>` in the background when a prompt names an in-scope or extras repo (1h cooldown). Each in-scope repo also has post-commit / post-checkout hooks plus a merge driver for `graph.json`.

## Ownership scope

Only repos whose `origin` owner is `amboss-mededu` or the authenticated GitHub user are graphified. Others are skipped entirely.

## Querying

Query the graph before reading source. Graph first, files second.

Never glob or grep the source repo as the opening move when a graph exists.

Always pass `--graph <path>`. Single-repo: the per-repo `graph.json`. Cross-repo: the supergraph.

- `graphify query "<question>" --graph <path>` — open-ended questions.
- `graphify path "<A>" "<B>" --graph <path>` — how two things relate.
- `graphify explain "<X>" --graph <path>` — single named entity.

If `graph.json` is missing, run `grip <name>` once, then query. If results reference ids not in the tree, re-run `grip <name>` and re-query. Don't preemptively rebuild.

After the query returns nodes, read the specific files at the lines they cite. Fall through to source search when the graph cannot answer. If graphifiable but not yet graphified: `grip add <path>` then `grip <name>`.

## Skill override

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
