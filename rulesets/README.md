# rulesets

Nothing under this directory auto-loads. The harness eagerly loads `~/.claude/rules/`, and these
bodies live outside it, so a session's user rules arrive through a hook that runs
`scripts/rulesets/resolve.py`. A hook that fails to run leaves the session with no rules at all.
That is the one consequence to hold before changing anything here.

## The five tiers

One directory per tier: `default`, `fable`, `opus`, `sonnet`, `haiku`. A tier maps to the model a
session or a delegate runs on, and `default` is where a lookup lands when no identifier matches.

A stem is a rule filename without its `.md` suffix, `writing-prose` for one. A tier resolves each
stem it composes to its own directory's file where that file exists, and to `default/`'s file
otherwise.

## manifest.yaml

The manifest carries one top-level key, `tiers`, whose value maps each of the five tier names to
that tier's entry. An entry takes one of two forms and never both.

- `include: "*"` composes every stem under `default/`. An optional `exclude` list of stems removes
  each one it names.
- `include:` followed by a list of stems states the composition outright, and carries no `exclude`.

Every tier key is required, so a new tier cannot appear by accident.

## models.yaml

`models.yaml` maps a tier to the model identifier prefixes that resolve to it. A lookup consults it
only where no `ANTHROPIC_DEFAULT_*_MODEL` variable names the running model. Adding a release means
adding a prefix, with no code change.

## Adding a tier override for one stem

To give `haiku` its own `writing-prose`:

1. Copy the body: `cp default/writing-prose.md haiku/writing-prose.md`.
2. Edit `haiku/writing-prose.md`. Leave the manifest alone, since `haiku` already composes
   `writing-prose` under `include: "*"`.
3. Confirm the layout is legal: `python3.14 ../scripts/rulesets/resolve.py check`.
4. Confirm the override resolves:
   `python3.14 ../scripts/rulesets/resolve.py inspect --tier haiku` prints `writing-prose` against a
   path under `haiku/`.

Deleting `haiku/writing-prose.md` resolves the stem back to `default/writing-prose.md`, and
`inspect` prints that path.

## Commands

Every command takes `--root DIR` to point its reads at an alternate rulesets root, defaulting to
this directory.

| Command | What it does |
| --- | --- |
| `resolve.py inspect --tier TIER` | Print each composed stem with its body path. Exits nonzero on any illegal state. |
| `resolve.py check` | Run `inspect` over all five tiers. Prints nothing on a legal layout and exits nonzero otherwise. |
| `resolve.py deliver` | Read a hook payload on stdin, dispatch on its `hook_event_name`, and emit hook JSON on stdout. |
| `resolve.py load-check --session ID` | Compare a session's load records against the manifest. Exits nonzero where any manifest stem auto-loaded. |
| `resolve.py delivery-check --session ID` | Compare a session's delivery records against each record's composition. Exits nonzero on any difference. |

`check` reports every illegal state rather than halting at the first: an unreachable body, a
composed stem with no body, a missing tier key, a tier mixing the wildcard and explicit forms, and
an exclusion naming a stem no directory holds.

## The two checks

`load-check` catches a regression that would put these bodies back into every model's context. It
exempts a CLAUDE.md at any scope, a nested CLAUDE.md, and a path-scoped rule loaded on a
`path_glob_match` reason. An `include` reason earns no exemption, because a `@path` import of a
manifest stem loads that stem everywhere.

`delivery-check` confirms each delivery carried the stems its tier composes. It treats a superseded
switch record as undelivered, since the harness drops a model switch's output where another switch
follows before the next request.

## Where the state lives

`RULESETS_STATE_DIR` overrides the state directory, and `~/.claude/.tmp/rulesets/` is the default.
`CLAUDE_CONFIG_DIR` overrides the configuration directory that every other path derives from.

- `audit/<session_id>/session.jsonl` holds a session's own load and delivery records.
- `audit/<session_id>/<agent_id>.jsonl` holds one delegate's records. Records partition by writer
  because a delegate can carry its parent's session identifier and two delegates can run at once.
- `audit/<session_id>/spawns.jsonl` holds the model a caller named for each spawn, which a
  delegate's start reads.
- `tiers/<session_id>` holds the session's resolved tier, which a later delivery reads where no
  model identifier is available.
