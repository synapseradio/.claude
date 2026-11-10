# Where records live

Records and state sit under `.tmp/rulesets-engine/` in the configuration directory, which is
`~/.claude` unless `CLAUDE_CONFIG_DIR` is set.

| Path | Holds |
| --- | --- |
| `audit/<session>/deliveries.jsonl` | one record for each delivery: the context's facts with their sources, each rule delivered with its variant and a SHA-256 digest of its file's text, and every skipped, withheld, and shown item |
| `audit/<session>/emitted-<part>.jsonl` | one record for each later part of a delivery |
| `audit/<session>/loads.jsonl` | the files the harness loaded |
| `audit/<session>/spawns.jsonl` | one record for each spawn, with the model its caller named, if any |
| `audit/<session>/claims.jsonl` | which delegate took which spawn record |
| `models/<session>.json` | the main session's model identifier, written at session start and at each model switch |
| `session/<session>.yaml` | the session's toggles |

A session's records share one directory under `audit/`. Removing it prunes that session's records
and leaves every other session's as they were. The model record sits in `models/`, outside that
directory, so pruning removes none.
