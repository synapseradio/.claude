# model-scoped-rulesets

Give each model you run its own rules, and see what each one received. A main session, the delegates
it spawns, and a second terminal often run different models at once, and each of them reads the tier
composed for the model it runs on.

## Words used here

- A **corpus** is the directory of rules you keep, outside `~/.claude/rules/`.
- A **manifest** is `manifest.yaml` at the corpus root, which states the stems each tier composes
  and the order they arrive in.
- A **stem** is one rule's name, `writing-prose` for one, which names its file, its marker, and its
  entries in the manifest.
- A **body** is one rule's file, `default/writing-prose.md` for one, and its text is what a model
  receives.
- A **marker** is the comment line a body opens on, `<!-- rule: writing-prose -->` for one, naming
  the stem that body carries.
- A **tier** is one directory of bodies, mapped to the model a context runs on.
- A **family tier** is one of the five the manifest requires: `default`, `fable`, `opus`, `sonnet`,
  and `haiku`. The last four name the model lines `models.yaml` maps identifiers to, so every
  identifier beginning `claude-haiku` reads the `haiku` tier. A tier named for one identifier,
  `claude-opus-4-8` for one, sits beside those five.
- An **override** is a body a tier holds under a stem `default/` also holds, which that tier reads
  in place of `default/`'s.
- An **exclusion** is a stem a tier's manifest entry leaves out, so no body for it reaches that tier.
- A **hook** is a command Claude Code runs on an event, whose output reaches the context that event
  opened.
- A **delegate** is an agent another context spawns, which resolves its own tier.
- A **fork** is a delegate that continues its parent's context on the parent's model.
- A **delivery** is one tier's text reaching one context, through a hook.
- A **part** is one slice of that text, carried by one hook command and headed with its place in the
  whole.
- A **render** is one tier read as a single document, written by `resolve.py render`.

## The picture

One corpus feeds every context, and each context receives the tier its model maps to, in parts.

```text
                                 rulesets/
                                     |
     +---------------+---------------+---------------+---------------+
     |               |               |               |               |
  session        delegate          fork         terminal 2     model switch
     |               |               |               |               |
 tier opus      tier haiku   the parent's tier  tier sonnet      tier opus
     |               |               |               |               |
 part 1..P       part 1..P       part 1..P       part 1..P       part 1..P
```

A fork runs the model its parent runs, so it reads the tier its parent read. P is how many parts
that tier packs into, and each part opens on a header naming its place, `part k of P`.

| The context | The event that delivers | The model | The tier it reads |
| --- | --- | --- | --- |
| a main session | `SessionStart` | opus | `opus`, 37 stems |
| a delegate it spawns | `SubagentStart` | haiku | `haiku`, 24 stems |
| a fork of that session | `SubagentStart` | the main model | the parent's tier |
| a second terminal | `SessionStart` | sonnet | `sonnet`, 35 stems |
| that terminal after `/model opus` | `PostModelSwitch` | opus | `opus`, 37 stems |

## What a context holds once the parts arrive

Each part carries a run of whole rules. Packing keeps a body entire, so every rule a part carries
arrives complete, and the parts together carry the tier's whole text.

Parts reach a context in the order their hooks finish, which is the order the harness returns them
in rather than the order they are registered in. Each header carries its own place, `part k of P`,
so the text says where a part sits and how many more to expect. The live corpus packs into 8 parts
for `default` and 4 for `haiku`, and the hook commands past part P emit nothing.

Headless sessions against this plugin received every part of their tier: 8 for `fable`, 7 for
`sonnet`, and 4 for `haiku`, each part between 760 and 8,864 characters, and none saved to a file.
The arrival order ran as the hooks finished, part 8 first in one run and part 3 first in another. A
haiku delegate and a sonnet delegate spawned from one fable session each received every part of its
own tier, 4 and 7, and `delivery-check` printed nothing for each session.

## Who this is for

- You run a cheap model on narrow work and want it reading the rules for that work alone. The
  `haiku` tier composes 24 stems and 24,761 characters a spawn, where `default` composes 37 stems
  and 57,245 characters.
- You want a delegate's rules to name only tools the delegate has. `sonnet` and `haiku` exclude
  `agent-delegation` and `spawn-decision`, and `haiku` also excludes `asking-questions`,
  `persistent-memory`, `worktrees`, `writing-code`, `writing-comments`, `data-modeling`,
  `debugging`, `repairing`, `claims`, `reasoning-guidelines`, and `inquiring`.
- You want one model's vendor guidance in that model's own words. `rulesets/opus/spawn-decision.md`
  holds seven sentences that reach `opus` alone.
- You want to see a changed rule arrive. `deliveries --session ID` prints one line per delivery that
  reached a context, and `delivery-check --session ID` compares each against its tier's composition.
- You want a variant of one rule for one model without a second copy of everything else. A tier
  directory holds the bodies that differ, and every other stem resolves to `default/`.
- You want a new model to have its own rules the day it ships. A directory named for its identifier
  and one key under `tiers:` give it a tier, with no code change.
- You want to read a tier as one document. `renders/<tier>/working-rules.md` is that read, written
  by `resolve.py render`.

## Where it pays most

The difference between tiers pays where several models run at once, where delegates run on cheaper
models, and where the corpus runs past a few kilobytes. With one model, no delegates, and a few
kilobytes of rules, `~/.claude/rules/` hands every context the same text, which is the same result
with no corpus to keep.

## What the numbers measure

Every number here counts stems, characters, or parts, measured on the live corpus with `resolve.py
inspect` and `pack_parts` in `lib/rulesets/resolve.py`.

| Tier | Stems | Characters | Parts at a 9,000-character budget |
| --- | --- | --- | --- |
| `default` | 37 | 57,245 | 8 |
| `fable` | 37 | 57,245 | 8 |
| `opus` | 37 | 57,121 | 8 |
| `sonnet` | 35 | 52,121 | 7 |
| `haiku` | 24 | 24,761 | 4 |

Those characters are what each context receives: a haiku delegate reads 24,761 of them where the
same spawn on `default` would read 57,245. How a model works under one tier against another is a
comparison you run: give one task to one model twice, once under each tier, and read the two
transcripts. `deliveries --session ID` names which rules each of those runs received.

## A five-minute walk

### 1. Create the corpus

```bash
resolve.py init
```

That writes `~/.claude/rulesets`: five tier directories, a manifest composing each, and
`models.yaml`, holding the identifier prefixes each family tier answers to. The hooks pass no
`--root`, so a command you run with none reads the corpus they read.

### 2. Write one rule

Write `~/.claude/rulesets/default/shell-quoting.md`, opening on `<!-- rule: shell-quoting -->`, and
add `shell-quoting` to the `order` list in `manifest.yaml` in the same change. `check` reports an
`order-mismatch` until both are there.

### 3. Withhold it from haiku

```yaml
  haiku:
    include: "*"
    exclude:
      - shell-quoting
```

### 4. Read what haiku now composes

```bash
resolve.py check                   # prints nothing and exits 0 on a legal corpus
resolve.py inspect --tier haiku    # each composed stem with its body path
```

`shell-quoting` is absent from that listing, and present under `--tier default`.

### 5. Spawn a haiku delegate

Start a session and ask for one, "spawn a haiku agent to list the files in this directory" for one.
The delegate's `SubagentStart` delivers the `haiku` tier.

### 6. Read what arrived

```bash
resolve.py deliveries --session <session_id>
resolve.py delivery-check --session <session_id>
```

The session identifiers are the directory names under `~/.claude/.tmp/rulesets/audit/`. The
delegate's line names the `haiku` tier and the stems it carried, and `shell-quoting` is not among
them.

## The corpus

```text
rulesets/
  manifest.yaml        which stems each tier composes, and the order delivery and the renders follow
  models.yaml          the identifier prefixes each family tier answers to
  default/             the bodies every tier falls back to
  fable/ opus/ sonnet/ haiku/
                       the bodies that tier overrides
  renders/<tier>/working-rules.md
                       a generated read of one tier, written by `render`
  references/          a catalog a body cites, carried with the corpus
```

The plugin carries the resolver, the hooks, and the packer that splits a tier into parts. The corpus
carries every rule body, the manifest that composes them, and the order both delivery and the
renders follow.

The root resolves in one order: `--root`, then `RULESETS_ROOT`, then `rulesets` under the
configuration directory, which is `CLAUDE_CONFIG_DIR` or `~/.claude`. The hooks pass no flag, so a
command you run by hand with none reads the corpus the hooks read. A symlink at that path is
followed like any other directory, so a corpus kept in your own dotfiles is delivered from where you
keep it.

A root that is not there yet gets scaffolded by the first delivering hook to run, on `SessionStart`,
`SubagentStart`, or `PostModelSwitch`: five empty tier directories, a manifest composing each, and
`models.yaml`. The `PreToolUse` hook records the spawn and returns before that, so it leaves the
corpus alone. A scaffolded corpus is legal, composes no stems, and the note closing the delivered
text says it was created.

A tier is one directory. `default` is where a lookup lands when no identifier matches, and a stem
with no file in its own tier resolves to `default/`'s file. A directory named for a model identifier
is a tier of its own once the manifest names it.

## How a model reaches its tier

A session's model reaches its tier through three sources, and the first match wins.

1. A tier whose name equals the running model identifier.
2. The four `ANTHROPIC_DEFAULT_*_MODEL` profile variables, in the order `opus`, `sonnet`, `haiku`,
   `fable`. Two variables naming one identifier resolve to the first in that order, and the
   delivered text names the collision.
3. The prefixes in `models.yaml`, where the longest match wins.

A delegate resolves separately, in `delegate_resolution` in `lib/rulesets/resolve.py`: from the
model its caller named for that spawn, then the pin, the model an agent definition names in its
`model` frontmatter, then `CLAUDE_CODE_SUBAGENT_MODEL`, then its parent's recorded tier. A fork runs
the main model, so it takes the parent's tier outright. Where two spawns of one agent type in one
prompt name different models, the per-spawn model is ambiguous, so that delegate resolves from the
pin onward and the delivered text carries a note naming the ambiguity.

## The hooks

| Event | Matcher | What runs | Commands |
| --- | --- | --- | --- |
| `SessionStart` | `startup`, `resume`, `clear`, `compact`, `fork` | deliver the session's tier | 10 per matcher, 50 in all |
| `SubagentStart` | — | deliver the delegate's tier | 10 |
| `PostModelSwitch` | — | deliver the tier switched to, where it differs from the one in play | 10 |
| `PreToolUse` | `Agent` | record the model the caller named for this spawn | 1 |
| `InstructionsLoaded` | — | record what the harness loaded | 1 |

Each delivering event registers `deliver.py --part 1` through `--part 10`, one command per part
slot, 72 commands in all. Every slot reads the same payload and emits its own part or nothing, so
`haiku`, which packs into 4 parts, leaves six slots silent.

Every command runs through `hooks/with-python.sh`, which runs the first interpreter that has PyYAML
and Python 3.12 or above: `RULESETS_PYTHON`, then `python3.14`, `python3.13`, `python3.12`,
`python3`.

These hooks are the channel the corpus travels by, so a context holds the rules its own hooks
delivered, and a context whose hook fails runs on whatever the harness loaded by itself. Delivery
falls back to the `default` tier wherever a tier, a manifest, or a body is unavailable, and names
what failed in the text it delivers.

Claude Code runs every hook registered for an event, from every source that registers one. A
settings file carrying its own entry for one of these events beside this plugin delivers the same
ruleset twice into one context.

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
| `migrate-rules` | Move each body of a rules directory that loads into every context into `default/`, and leave the ones whose `paths:` frontmatter scopes them to named files where the harness reads them. `--dry-run` prints the moves and makes none, and `--undo` reverses the last run. |
| `render` | Write one render per tier. `--check` reports drift, `--model NAME` scopes a run to one tier, and `--reverse` splits `default/`'s render back into `CLAUDE.md` and the bodies under `default/`. |
| `deliver` | Read a hook payload on stdin and emit hook JSON on stdout. `hooks/deliver.py` is the script the hooks run, and it takes `--part K` to emit part K alone. |
| `deliveries --session ID` | Print one line per delivery that reached a context. |
| `delivery-check --session ID` | Compare each delivery's stems against its tier's composition, and each part from 2 to P against its own writer's emitted record, digest included. |
| `load-check --session ID` | Report any file whose stem a tier composes that the harness loaded on its own. |

`check` reports every illegal state rather than halting at the first: an unreachable body, a composed
stem with no body, a missing tier key, a tier mixing the wildcard `include: "*"` with an explicit
list of stems, an exclusion naming a stem no directory holds, an order disagreeing with `default/`, a
directory that is neither a tier nor reserved, a body naming another stem, a citation of a reference
the corpus does not carry, a body longer than one part's budget, and a tier needing more than ten
parts.

`load-check` exempts by stem and not by load reason. A file named `CLAUDE.md` at any scope is exempt,
and so is any file whose stem no tier composes, which is how a rule scoped to named paths by its
`paths:` frontmatter passes. A file whose stem the manifest names is reported whatever reason loaded
it.

## The renders

A render is one tier read as a single document: the preamble, which is the text of `CLAUDE.md` in
the configuration directory, then every body the tier delivers, in the order the manifest's `order`
list names. The render composes the way delivery does: a stem the tier holds no body for shows
`default/`'s body, a stem the tier overrides shows the tier's own, and a stem the tier's manifest
entry leaves out is absent. A manifest stating no order renders sorted. A render is for a reader,
and delivery and every lookup read the bodies themselves. The two directions reproduce each other
byte for byte, and a write refuses over a target carrying changes git has not seen.

A render puts one tier beside another, and one tier beside its own earlier form, as documents you
can diff. The delivery records hold the other half: which rules each run received.

## What the record covers

The records name what the plugin emitted to each context: the tier it resolved, the stems that tier
composed, and each part with its digest, the sha256 of that part's text. The record reaches as far
as the emitted bytes, and what a model did with those bytes reads from its transcript.

Each writer keeps its own records, and `delivery-check` reads them that way: for a delivery of P
parts, each part from 2 to P needs its own emitted record from that same writer, so two deliveries
by one writer need two records for each part. Each emitted digest is compared against the sha256 of
that part as the tier composes now, and a digest that disagrees prints its own line. So the
comparison is against the corpus as it stands when the check runs, and a corpus edited since a
session ran reports that session's parts as differing.

The record names the tier a context resolved and the source it resolved from, which is where a
session that reached an unexpected tier shows it. Under `claude -p --model haiku` the `SessionStart`
payload carried no `model` field, and the tier resolved from the `ANTHROPIC_MODEL` variable where it
was set and to `default` where it was not.

## Where the state lives

`RULESETS_STATE_DIR` overrides the state directory, and `<config>/.tmp/rulesets/` is the default. The
records are of what loaded and what was delivered, so they sit outside the corpus and nothing under
version control there grows one file per session.

- `audit/<session_id>/session.jsonl`: one session's own load and delivery records.
- `audit/<session_id>/session.part<k>.jsonl`: one part's emitted record, one file per part slot.
- `audit/<session_id>/<agent_id>.jsonl` and `<agent_id>.part<k>.jsonl`: one delegate's records, kept
  apart because a delegate can carry its parent's session identifier and two delegates can run at
  once.
- `audit/<session_id>/spawns.jsonl`: the model a caller named for each spawn.
- `tiers/<session_id>`: the session's resolved tier, read where no model identifier is available.

The files partition by writer, and `read_records_for` in `lib/rulesets/audit.py` reads one writer's
set: `session.jsonl` with every `session.part<k>.jsonl` beside it, or `<agent_id>.jsonl` with its own
part files. That is how a check tells a session's parts from a delegate's when the two share a
session identifier, a part number, and a total.

## Requirements

Python 3.12 or above with PyYAML, and git where you want the render's refusal to see uncommitted
changes.
