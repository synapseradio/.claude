# rulesets

Claude Code loads every file under `~/.claude/rules/` into every context, whichever model runs. A
rule only a large model can follow reaches a small one too, and a rule a small model needs reaches
the large one. This directory gives each model its own set of rules instead.

## Terms

- A **rule** is one instruction set with one name, `writing-prose` for one.
- A **stem** is that name: the rule's filename without its `.md` suffix. The same stem names the
  file, the marker on its first line, the entry in the manifest's `order` and `exclude` lists, and
  the section in a render. Where this README says a tier composes, excludes, or resolves a stem, it
  means the rule that stem names.
- A **body** is one rule's file under a tier directory, `default/writing-prose.md` for one. Its
  text is what delivery hands the model.
- A **marker** is the line `<!-- rule: stem -->`, which tells a reader where one rule ends and the
  next begins. A body may open on its own marker or carry none. Delivery derives the line for a
  body carrying none and reads a body carrying its own verbatim.
- A **tier** is one directory of bodies, mapped to the model a session or a delegate runs on.
- A **composition** is the set of stems one tier delivers, each resolved to the body it reads.
- A **render** is one tier read as a single document, written by `resolve.py render`.

## Layout

```text
rulesets/
  manifest.yaml            which stems each tier composes, and the order the renders follow
  models.yaml              the identifier prefixes each family tier answers to
  default/                 the bodies every tier falls back to
  fable/ opus/ sonnet/ haiku/
                           each family tier's own bodies, where they differ from default/
  claude-opus-4-8/         a tier for one model, named for its identifier
  renders/<tier>/working-rules.md
                           a generated read of one tier
  references/              a catalog a body may cite, carried with the corpus; absent until one is needed
```

Five family tiers are required: `default`, `fable`, `opus`, `sonnet`, `haiku`. `default` is where
a lookup lands when no identifier matches, and it is the directory every other tier falls back to.
Any further tier names one model, and its directory name is the model identifier. `renders` and
`references` are reserved, so a directory here is a tier, one of those two, or an illegal state.

## How a tier composes

A tier resolves each stem it composes to its own directory's file where that file exists, and to
`default/`'s file otherwise. So a tier directory holds only the bodies that differ, and a tier
whose directory is empty delivers every stem it composes from `default/`.

`manifest.yaml` says which stems each tier composes. Its `tiers` key maps each tier name to an
entry, and an entry takes exactly one of two forms.

- `include: "*"` composes every stem under `default/`. An optional `exclude` list names stems to
  leave out of this tier.
- `include:` followed by a list of stems states the composition outright, and carries no
  `exclude`.

All five family keys are required, so a family tier cannot appear by accident. A model tier exists
once it has both a directory and a key: a directory with no key composes nothing, and `check`
reports every body in it as unreachable.

The manifest's `order` key lists the stems of `default/` in the sequence the renders follow. It is
optional, and a manifest carrying none renders sorted. Delivery composes in sorted order whatever
the list says, so the list orders the renders alone.

`models.yaml` maps each family to the identifier prefixes that resolve to it, and the longest
matching prefix wins. Keep its entries to prefixes a whole family shares. A model listed under a
family here reads that family's bodies, and the entry then has to be found and removed before the
model's own directory takes effect.

## How the rules reach a session

Nothing here loads on its own. A hook from the model-scoped-rulesets plugin delivers each session
its tier, so if the hook fails, the session runs with no rules.

The plugin carries the mechanism and no rules. This directory carries the rules: the bodies, the
manifest that composes them, the order the renders follow, and the renders. The plugin finds it at
`--root`, then `RULESETS_ROOT`, then `~/.claude/rulesets`, which is this directory. Every command
this README names is `resolve.py` under the installed plugin's `lib/rulesets/`, and each takes
`--root DIR` to read a corpus other than this one. The plugin's own README, at
`../features/model-scoped-rulesets/README.md`, covers the hooks, how a delegate resolves, and the
interpreter it runs on.

## How a model reaches its tier

The lookup tries three sources in order, and the first match wins.

1. A tier whose name equals the running model identifier.
2. The four `ANTHROPIC_DEFAULT_*_MODEL` profile variables, in the order `opus`, `sonnet`, `haiku`,
   `fable`. Two variables naming one identifier resolve to the first in that order, and the
   delivered text names the collision.
3. The prefixes in `models.yaml`.

The first source sits above the second so that one model lives in one place. With the order
reversed, `ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-8` would send that model to the `opus` tier,
and its own directory would sit unread until someone found the variable.

## Recipes

### Add a rule every tier delivers

1. Write the body at `default/<stem>.md`, opening on `<!-- rule: <stem> -->`.
2. Add `<stem>` to the `order` list in `manifest.yaml`, in the same change.
3. Run `resolve.py check`, then `resolve.py render`.

### Give one tier its own text for a rule

1. Copy the body: `cp default/writing-prose.md haiku/writing-prose.md`.
2. Edit `haiku/writing-prose.md`. The manifest needs no change, since `haiku` already composes
   the stem under `include: "*"`.
3. Run `resolve.py check`, then `resolve.py inspect --tier haiku`, which prints `writing-prose`
   against a path under `haiku/`.
4. Run `resolve.py render`.

Deleting `haiku/writing-prose.md` resolves the stem back to `default/writing-prose.md`.

### Withhold a rule from one tier

1. Add the stem to that tier's `exclude` list in `manifest.yaml`:

   ```yaml
   sonnet:
     include: "*"
     exclude:
       - agent-delegation
   ```

2. Run `resolve.py check`, then `resolve.py inspect --tier sonnet`, which no longer prints the
   stem.
3. Run `resolve.py render`. The tier's render leaves that section out.

### Give one model its own tier

1. Create `rulesets/<identifier>/`, `rulesets/claude-opus-4-8/` for one.
2. Add a `<identifier>:` key under `tiers:` in `manifest.yaml`, at `include: "*"`.
3. Put the bodies that differ in that directory. Every other stem resolves to `default/`.
4. Run `resolve.py check`, then `resolve.py inspect --tier <identifier>`, then `resolve.py render`.

No step touches `models.yaml` or any code.

## The renders

`renders/<tier>/working-rules.md` shows what a model on that tier reads, as one document: the
preamble from `CLAUDE.md`, then every body the tier delivers, in the order the manifest's `order`
list names. The render composes the way delivery does. A stem the tier holds no body for shows the
section it reaches in `default/`, a stem the tier overrides shows the tier's own, and a stem the
tier excludes is left out. Nothing loads a render, and no lookup resolves through it.

`resolve.py render` writes one render per tier directory.

- `--model NAME` scopes a run to the tier it names.
- `--check` reports drift and writes nothing.
- `--reverse` splits `default/`'s render back into `CLAUDE.md` and the bodies under `default/`,
  so an edit made in that render reaches the files delivery reads.

A run in either direction overwrites its target whole. It refuses a target carrying changes git
has not seen, since those changes would vanish with no diff to recover them from. Commit them and
run again. Where an earlier forward run wrote those changes, which `--check` confirms by reporting
the render current, restore the render with `git checkout HEAD -- <path>` instead.

## Commands

| Command | What it does |
| --- | --- |
| `check` | Run `inspect` over every tier the manifest names. Prints nothing on a legal layout and exits nonzero otherwise. |
| `inspect --tier TIER` | Print each composed stem with its body path. Exits nonzero on any illegal state. |
| `render` | Write one render per tier, or check them with `--check`, or split `default/`'s back with `--reverse`. |
| `init` | Write a legal and empty corpus: the five tier directories, a manifest composing each, and the family prefixes. Refuses a root that already holds a manifest. |
| `migrate-rules` | Move the frontmatter-less bodies of `~/.claude/rules/` into `default/`, leaving the path-scoped ones where the harness reads them. `--dry-run` prints the moves and makes none, and `--undo` reverses the last run. |
| `deliver` | Read a hook payload on stdin and emit hook JSON on stdout. The hooks run this command. |
| `deliveries --session ID` | Print one line per delivery that reached a context. |
| `delivery-check --session ID` | Compare a session's deliveries against each record's composition. Exits nonzero on any difference. |
| `load-check --session ID` | Compare a session's load records against the manifest. Exits nonzero where any manifest stem auto-loaded. |

## What check reports

`check` reports every illegal state it finds rather than halting at the first. Each finding
carries one of these kinds.

| Kind | The state |
| --- | --- |
| `manifest` | The manifest is missing or does not parse. |
| `missing-tier` | A family tier has no key under `tiers`. |
| `bad-form` | A tier's entry is not a mapping, or states no `include` of either form. |
| `mixed-form` | A tier mixes the wildcard into an include list, or states an include list beside an `exclude`. |
| `stale-exclusion` | An `exclude` names a stem no tier directory holds. |
| `no-body` | A composed stem has no body in the tier's directory nor in `default/`. |
| `unreachable-body` | A body sits in a tier directory and reaches no composition. |
| `order-mismatch` | The `order` list and the stems of `default/` disagree. |
| `misnamed-body` | A body's first line is a marker naming a different stem. |
| `stray-directory` | A directory here is neither a tier the manifest names nor reserved. |
| `reserved-tier` | A manifest key names a reserved directory. |
| `dangling-reference` | A body cites a file under `references/` that is not there. |
| `external-reference` | A body cites `~/.claude/references/`, which the corpus does not carry. |

`misnamed-body` guards the delivered text: a body carrying another stem's marker names the wrong
rule in every context it reaches.

## The two session checks

`load-check` catches a regression that would put these bodies back into every model's context. It
exempts by stem and not by load reason. A file named `CLAUDE.md` at any scope is exempt, and so is
any file whose stem no tier composes, which is how a path-scoped rule under `~/.claude/rules/`
passes. A file whose stem the manifest names is reported whatever reason loaded it, since a
`@path` import of a manifest stem puts that stem into every model's context exactly as an eager
load would.

`delivery-check` confirms each delivery carried the stems its tier composes. It treats a superseded
switch record as undelivered, since the harness drops a model switch's output where another switch
follows before the next request.

## Where the state lives

The records of what loaded and what was delivered sit outside the corpus, so nothing under version
control here grows one file per session. `RULESETS_STATE_DIR` overrides the state directory, and
`~/.claude/.tmp/rulesets/` is the default. `CLAUDE_CONFIG_DIR` overrides the configuration
directory that both the state and this corpus derive from.

- `audit/<session_id>/session.jsonl` holds a session's own load and delivery records.
- `audit/<session_id>/<agent_id>.jsonl` holds one delegate's records. Records partition by writer
  because a delegate can carry its parent's session identifier and two delegates can run at once.
- `audit/<session_id>/spawns.jsonl` holds the model a caller named for each spawn, which a
  delegate's start reads.
- `tiers/<session_id>` holds the session's resolved tier, which a later delivery reads where no
  model identifier is available.
