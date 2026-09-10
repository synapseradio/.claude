# model-scoped-rulesets

Deliver a different set of user rules to each model Claude Code runs.

Claude Code loads everything under `~/.claude/rules/` into every context, whichever model is
running. This plugin reads a corpus you keep outside that directory and delivers one tier of it per
context, chosen by the model in play. A rule that only a large model can follow reaches that model,
and a rule a small one needs reaches the small one.

The plugin ships mechanism and no rules. The corpus holds every rule body, the manifest that
composes them, and the order the renders follow. Nothing in it auto-loads, so the hooks below are
the only channel by which a session receives it, and a hook that fails leaves the session with no
rules. Delivery therefore falls back to the `default` tier wherever a tier, a manifest, or a body is
unavailable, and names what failed in the text it delivers.

## The corpus

```text
rulesets/
  manifest.yaml        which stems each tier composes, and the order the renders follow
  models.yaml          the identifier prefixes each family tier answers to
  default/             the bodies every tier falls back to
  fable/ opus/ sonnet/ haiku/
                       the bodies that tier overrides
  renders/<tier>/working-rules.md
                       a generated read of one tier, written by `render`
  references/          a catalog a body cites, carried with the corpus
```

The root resolves in one order: `--root`, then `RULESETS_ROOT`, then `rulesets` under the
configuration directory, which is `CLAUDE_CONFIG_DIR` or `~/.claude`. The hooks pass no flag, so a
command you run by hand with none reads the corpus the hooks read. A symlink at that path is
followed like any other directory, which is how a corpus kept in your own dotfiles stays yours.

A root that is not there yet gets scaffolded on the first hook run: five empty tier directories, a
manifest composing each, and the family prefixes. That corpus is legal and delivers nothing, and
the delivered header says it was created.

A tier is one directory. `default` is where a lookup lands when no identifier matches, and a stem
with no file in its own tier resolves to `default/`'s file. A directory named for a model identifier
is a tier of its own once the manifest names it.

## How a model reaches its tier

Three sources, first match winning:

1. A tier whose name equals the running model identifier.
2. The four `ANTHROPIC_DEFAULT_*_MODEL` profile variables, in the order `opus`, `sonnet`, `haiku`,
   `fable`. Two variables naming one identifier resolve to the first in that order, and the
   delivered text names the collision.
3. The prefixes in `models.yaml`, where the longest match wins.

A delegate resolves separately, from the model its caller named for that spawn, then the agent
definition's pin, then `CLAUDE_CODE_SUBAGENT_MODEL`, then its parent's recorded tier. A fork runs
the main model, so it takes the parent's tier outright.

## The hooks

| Event | Matcher | What runs |
| --- | --- | --- |
| `SessionStart` | `startup`, `resume`, `clear`, `compact`, `fork` | deliver the session's tier |
| `SubagentStart` | — | deliver the delegate's tier |
| `PostModelSwitch` | — | deliver the tier switched to, where it differs from the one in play |
| `PreToolUse` | `Agent` | record the model the caller named for this spawn |
| `InstructionsLoaded` | — | record what the harness loaded |

Every command runs through `hooks/with-python.sh`, which execs the first interpreter that has PyYAML
and Python 3.12 or above: `RULESETS_PYTHON`, then `python3.14`, `python3.13`, `python3.12`,
`python3`.

Claude Code does not deduplicate hooks across sources. A settings file carrying an entry for one of
these events beside this plugin delivers the same ruleset twice into one context.

## The markers

A body may open on `<!-- rule: stem -->`, where the stem is its filename, or carry no marker at all.
Delivery derives the line for a body carrying none and reads a body carrying its own verbatim, so
both forms deliver as written and the renders keep each body in the form it has. A body whose first
line is a marker naming a different stem is an illegal state, which `check` reports as
`misnamed-body`.

## The commands

`lib/rulesets/resolve.py` carries every command. Each takes `--root DIR` to read an alternate
corpus.

| Command | What it does |
| --- | --- |
| `init` | Write a legal and empty corpus. Refuses a root that already holds a manifest. |
| `check` | Report every illegal state across every tier the manifest names. Exits nonzero on any. |
| `inspect --tier TIER` | Print each composed stem with its body path. |
| `migrate-rules` | Move the frontmatter-less bodies of a rules directory into `default/`, leaving the path-scoped ones where the harness reads them. `--dry-run` prints the moves and makes none, and `--undo` reverses the last run. |
| `render` | Write one render per tier. `--check` reports drift, `--model NAME` scopes a run to one tier, and `--reverse` splits `default/`'s render back into `CLAUDE.md` and the bodies under `default/`. |
| `deliver` | Read a hook payload on stdin and emit hook JSON on stdout. This is what the hooks run. |
| `deliveries --session ID` | Print one line per delivery that reached a context. |
| `delivery-check --session ID` | Compare each delivery's stems against its tier's composition. |
| `load-check --session ID` | Report any file whose stem a tier composes that the harness loaded on its own. |

`check` reports every illegal state rather than halting at the first: an unreachable body, a composed
stem with no body, a missing tier key, a tier mixing the wildcard and explicit forms, an exclusion
naming a stem no directory holds, an order disagreeing with `default/`, a directory that is neither a
tier nor reserved, a body naming another stem, and a citation of a reference the corpus does not
carry.

`load-check` exempts by stem and not by load reason. A file named `CLAUDE.md` at any scope is exempt,
and so is any file whose stem no tier composes, which is how a path-scoped rule passes. A file whose
stem the manifest names is reported whatever reason loaded it.

## The renders

A render is one tier read as a single document: the preamble from `CLAUDE.md`, then the bodies that
tier's own directory holds, in the order the manifest's `order` list names. A manifest stating no
order renders sorted. Nothing loads a render and no lookup resolves through it. The two directions
reproduce each other byte for byte, and a write refuses over a target carrying changes git has not
seen.

## Where the state lives

`RULESETS_STATE_DIR` overrides the state directory, and `<config>/.tmp/rulesets/` is the default. The
records are of what loaded and what was delivered, so they sit outside the corpus and nothing under
version control there grows one file per session.

- `audit/<session_id>/session.jsonl`: one session's own load and delivery records.
- `audit/<session_id>/<agent_id>.jsonl`: one delegate's records, kept apart because a delegate can
  carry its parent's session identifier and two delegates can run at once.
- `audit/<session_id>/spawns.jsonl`: the model a caller named for each spawn.
- `tiers/<session_id>`: the session's resolved tier, read where no model identifier is available.

## Requirements

Python 3.12 or above with PyYAML, and git where you want the render's refusal to see uncommitted
changes.
