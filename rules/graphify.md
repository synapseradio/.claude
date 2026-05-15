# graphify

When the user invokes graphify, references a repo under `~/projects/`, or runs graphify commands.

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

## Reference

For layout, the `grip` command surface, the SKILL override, save-result mechanics, and forced-reset recovery, see [../references/graphify-reference.md](../references/graphify-reference.md).
