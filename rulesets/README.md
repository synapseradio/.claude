# rulesets

Nothing under this directory auto-loads. The harness eagerly loads `~/.claude/rules/`, and these
bodies live outside it, so a session's user rules arrive through a hook the model-scoped-rulesets
plugin ships. A hook that fails to run leaves the session with no rules at all. That is the one
consequence to hold before changing anything here.

The plugin carries the mechanism and no rules. This directory carries the rules: the bodies, the
manifest that composes them, the order the renders follow, and the renders. The plugin finds it at
`--root`, then `RULESETS_ROOT`, then `~/.claude/rulesets`, which is here.

## Tiers

A tier is one directory, and it maps to the model a session or a delegate runs on. `default` is
where a lookup lands when no identifier matches.

Five family tiers are required: `default`, `fable`, `opus`, `sonnet`, `haiku`.

Any further tier names one model, and its directory name is the model identifier,
`claude-opus-4-8` for one. A lookup matches such a tier ahead of the family, so the model needs no
entry in `models.yaml`.

A stem is a rule filename without its `.md` suffix, `writing-prose` for one. A tier resolves each
stem it composes to its own directory's file where that file exists, and to `default/`'s file
otherwise.

## How a model reaches its tier

`tier_lookup` tries three sources in order, and the first match wins.

1. A tier whose name equals the running model identifier.
2. The four `ANTHROPIC_DEFAULT_*_MODEL` profile variables, in the order `opus`, `sonnet`, `haiku`,
   `fable`. Two variables naming one identifier resolve to the first in that order, and the
   delivered text names the collision.
3. The prefixes in `models.yaml`, where the longest match wins.

The first source sits above the second so that one model lives in one place. With the order
reversed, `ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-8` would send that model to the `opus` tier,
and its own directory would sit unread until someone found the variable.

## manifest.yaml

The manifest carries two top-level keys. `tiers` maps each tier name to that tier's entry, and an
entry takes one of two forms and never both.

- `include: "*"` composes every stem under `default/`. An optional `exclude` list of stems removes
  each one it names.
- `include:` followed by a list of stems states the composition outright, and carries no `exclude`.

All five family keys are required, so a family tier cannot appear by accident. The manifest is also
what admits a model tier: a directory with no key here composes nothing, and `check` reports every
body in it as unreachable.

`order` lists the stems of `default/` in the sequence the renders follow. It is optional, and a
manifest carrying none renders its stems sorted. Adding an always-on body adds its stem to that
list in the same change, and `check` reports an `order-mismatch` where the list and the directory
disagree. Delivery composes in sorted order whatever the list says, so the list orders the renders
alone.

## models.yaml

`models.yaml` maps a family to the identifier prefixes that resolve to it, and the longest matching
prefix wins. A lookup consults it only where no tier is named for the running identifier and no
`ANTHROPIC_DEFAULT_*_MODEL` variable names it.

Keep these entries to prefixes a whole family shares. To give one model its own rules, create its
directory and add its manifest key, as below. A model listed under a family here reads that
family's bodies, and the entry then has to be found and removed before the model's own directory
takes effect.

## Adding a tier for one model

To give Opus 4.8 rules of its own:

1. Create `rulesets/claude-opus-4-8/`, naming the directory for the model identifier.
2. Add a `claude-opus-4-8:` key under `tiers:` in `manifest.yaml`, at `include: "*"`.
3. Put the bodies that differ in that directory. Every stem with no file there resolves to
   `default/`.
4. Confirm it resolves: `resolve.py inspect --tier claude-opus-4-8`.

Neither step touches `models.yaml`, and neither touches any code.

## Adding a tier override for one stem

To give `haiku` its own `writing-prose`:

1. Copy the body: `cp default/writing-prose.md haiku/writing-prose.md`.
2. Edit `haiku/writing-prose.md`. Leave the manifest alone, since `haiku` already composes
   `writing-prose` under `include: "*"`.
3. Confirm the layout is legal: `resolve.py check`.
4. Confirm the override resolves: `resolve.py inspect --tier haiku` prints `writing-prose` against
   a path under `haiku/`.

Deleting `haiku/writing-prose.md` resolves the stem back to `default/writing-prose.md`, and
`inspect` prints that path.

## The renders

`renders/$tier/working-rules.md` is a generated read of one tier: the preamble from `CLAUDE.md`
followed by every body that tier delivers, in the order `manifest.yaml`'s `order` list names.
Nothing loads it, and no lookup resolves through it. The render composes the way delivery does, so
a stem the tier holds no body for shows the section it reaches in `default/`, and a stem the tier
overrides shows the tier's own. The render is what the model reads, not the diff against `default/`.

`resolve.py render` writes one render per tier directory. `--model NAME` scopes a run to the
directory it names, `--check` reports drift and writes nothing, and `--reverse` splits `default/`'s
render back into `CLAUDE.md` and the bodies under `default/`. A run refuses to write over a target
carrying changes git has not seen.

## Commands

Every command takes `--root DIR` to point its reads at an alternate corpus, defaulting to
`~/.claude/rulesets`, which is this directory. The commands live at
`resolve.py` under the installed plugin's `lib/rulesets/`.

| Command | What it does |
| --- | --- |
| `resolve.py inspect --tier TIER` | Print each composed stem with its body path. Exits nonzero on any illegal state. |
| `resolve.py init` | Write a legal and empty corpus: the five tier directories, a manifest composing each, and the family prefixes. Refuses a root that already holds a manifest. |
| `resolve.py migrate-rules` | Move the frontmatter-less bodies of `~/.claude/rules/` into `default/`, leaving the path-scoped ones where the harness reads them. `--dry-run` prints the moves and makes none, and `--undo` reverses the last run. |
| `resolve.py render` | Write one render per tier, or check them with `--check`, or split `default/`'s back with `--reverse`. |
| `resolve.py check` | Run `inspect` over every tier the manifest names, model tiers included. Prints nothing on a legal layout and exits nonzero otherwise. |
| `resolve.py deliver` | Read a hook payload on stdin, dispatch on its `hook_event_name`, and emit hook JSON on stdout. |
| `resolve.py load-check --session ID` | Compare a session's load records against the manifest. Exits nonzero where any manifest stem auto-loaded. |
| `resolve.py delivery-check --session ID` | Compare a session's delivery records against each record's composition. Exits nonzero on any difference. |

`check` reports every illegal state rather than halting at the first: an unreachable body, a
composed stem with no body, a missing tier key, a tier mixing the wildcard and explicit forms, an
exclusion naming a stem no directory holds, an order that disagrees with `default/`, a directory
that is neither a tier nor reserved, and a body whose first line is a rule marker naming a
different stem.

That last one guards the delivered text. The `<!-- rule: stem -->` line is what tells a reader
where one rule ends and the next begins, and the stem is the filename, so delivery derives the line
for a body carrying none and reads a body carrying its own verbatim. A body carrying someone
else's names the wrong rule in every context it reaches.

## The two checks

`load-check` catches a regression that would put these bodies back into every model's context. It
exempts by stem and not by load reason: a file named `CLAUDE.md` at any scope is exempt, and so is
any file whose stem no tier composes, which is how a path-scoped rule under `~/.claude/rules/`
passes. A file whose stem the manifest names is reported whatever reason loaded it, since a `@path`
import of a manifest stem puts that stem into every model's context exactly as an eager load
would.

`delivery-check` confirms each delivery carried the stems its tier composes. It treats a superseded
switch record as undelivered, since the harness drops a model switch's output where another switch
follows before the next request.

## Where the state lives

`RULESETS_STATE_DIR` overrides the state directory, and `~/.claude/.tmp/rulesets/` is the default.
`CLAUDE_CONFIG_DIR` overrides the configuration directory that both the state and this corpus
derive from. The records sit outside the corpus, so nothing under version control here grows one
file per session.

- `audit/<session_id>/session.jsonl` holds a session's own load and delivery records.
- `audit/<session_id>/<agent_id>.jsonl` holds one delegate's records. Records partition by writer
  because a delegate can carry its parent's session identifier and two delegates can run at once.
- `audit/<session_id>/spawns.jsonl` holds the model a caller named for each spawn, which a
  delegate's start reads.
- `tiers/<session_id>` holds the session's resolved tier, which a later delivery reads where no
  model identifier is available.
