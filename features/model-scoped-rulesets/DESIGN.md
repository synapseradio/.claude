# How delivery works

Delivery reaches a context through hooks that fire as that context opens, and each section below
states one property it holds, the mechanism that reaches it, and what that mechanism costs.

## Every context gets its own delivery

Each session, each delegate, each fork, and each model switch receives the tier composed for the
model it runs on, computed at the moment that context starts.

A directory of rules holds one state for every reader: whatever is in `~/.claude/rules/` when a
context starts is what every context starting then reads. A per-context choice needs a per-context
event, so delivery rides on the events that fire as a context opens. `SessionStart` covers
`startup`, `resume`, `clear`, `compact`, and `fork`; `SubagentStart` covers a delegate; and
`PostModelSwitch` covers a model changing under a running session. Each hook reads the model from
its own payload, resolves a tier, and returns that tier's text as `additionalContext`.

The cost is that rules arrive at a context's start and at no other moment. An edit to a body reaches
the next context to start, and the contexts already running keep what they received.

## Rules follow the model, and agents follow the role

A tier states the rules for a model. An agent definition states a role and pins the model that role
runs on. The two meet at the model identifier alone.

A delegate's tier resolves from four sources in order, ranked in `delegate_resolution` in
`lib/rulesets/resolve.py`: the model the caller named for that spawn, recorded by the `PreToolUse`
hook on `Agent`; the agent definition's `model` frontmatter, read by `definition_pin` in the same
module; `CLAUDE_CODE_SUBAGENT_MODEL`; and the parent session's recorded tier. So a definition that
pins `haiku` picks up whatever the `haiku` tier composes, and rewriting that tier changes every
haiku delegate without touching one definition. A fork takes the parent's tier outright, since a
fork runs the main model.

A delegate whose launch delivery is recorded keeps that tier ahead of every source above, the force
levers and the fork rule included. `SubagentStart` fires again when a delegate resumes or a
teammate takes a new message, each time under a new `prompt_id` that matches no spawn record, so
without the launch record a compacted delegate would receive its parent's rules.

`definition_pin` reads a pin from three places. A plugin-scoped type such as `kit:reviewer` reads
the `agents/` directory under each install path `plugins/installed_plugins.json` records for that
plugin. Any other type reads the configuration directory's `agents/`, then `BUILT_IN_PINS`, which
holds the two built-ins whose documented model is fixed. A definition registers under its `name`
field, or under its filename where it names none.

The same `PreToolUse` hook denies a spawn that names no model when its agent type is not `fork` and
its pin is absent or `inherit`, telling the caller to retry with `model` set. So every delegate but
a fork runs on a model its caller or its definition named. The costs are two. `Explore`, `Plan`,
and `general-purpose` inherit the main model and pin none, so every call to them names a model.
`BUILT_IN_PINS` copies the docs by hand and goes stale if Claude Code changes a built-in's model.

## The whole ruleset arrives inline, in parts

A context receives the full text of its tier in its message stream, with no file to open and no
preview to expand.

Claude Code caps each hook output string at 10,000 characters; a larger `additionalContext` is
written to a file, and the model sees a 2 KB preview and a path
(https://code.claude.com/docs/en/hooks.md). All matching hooks for an event run in parallel, and
where several return `additionalContext` for one event, the model receives all of the values. So
delivery splits a tier across `PART_SLOTS = 10` hook commands at `PART_BUDGET = 9000` characters
each, giving up to 90,000 characters inline.

A measurement run reached that ceiling: ten command hooks on `SessionStart`, each returning 9,000
characters, 90,000 in sum, across three headless haiku sessions. All ten outputs reached the model
whole in every run, the model quoted each block's closing line, and no output was written to a file.

Packing keeps whole stems. A body never splits across parts, and a body longer than the budget sits
alone in its part. Every header names the part's place, `part k of P`, so a part that did not arrive
shows as a gap in the sequence.

A delivered part never passes 10,000 characters. `PART_CAP = 10000` sits beside `PART_BUDGET` in
`lib/rulesets/resolve.py`: the budget bounds the bodies a part carries, and the cap bounds the part
as delivered, header and trailer included. The last part carries the trailer, so `delivery_trailer`
takes the room left under the cap. The source line always survives whole, a note that does not fit
is clipped and ends in ` (clipped; check lists the rest)`, and a note with no room left is dropped.
Packing never reads a note, so clipping moves no boundary. A fallback whose reason ran 7,288
characters under an 8,900-character body delivers a last part of exactly 10,000 characters.

On the live corpus the largest part measured 8,874 characters with its header, and that corpus packs
into 8 parts for `default`, `fable`, `opus`, and `claude-opus-4-8`, 7 for `sonnet`, and 4 for
`haiku`.

Headless sessions against this plugin received those parts whole: `fable` 8, `sonnet` 7, and `haiku`
4, each part between 760 and 8,864 characters, and no part was saved to a file. Parts reached
context in the order their hooks finished, part 8 first in one run and part 3 first in another. A
haiku delegate and a sonnet delegate spawned from one fable session each received every part of its
own tier, 4 and 7, from the source `the per-spawn model`. `delivery-check` printed nothing for each
of those sessions.

The cost has three edges. A body longer than the budget occupies a whole part by itself, which
`check` reports as `oversize-body`. A tier that needs more than ten parts does not fit the slots,
reported as `too-many-parts`, which leaves the live corpus's largest tier two slots of room. A long
failure reason reaches the context clipped, and `check` lists it whole.

## The same bytes every time

One corpus and one tier produce one set of parts, byte for byte, on every delivery.

`pack_parts` is a pure function of the composed sections and the budget: greedy, whole sections, in
composed order. Nothing above the trailer carries a timestamp, a session identifier, or a filesystem
path, so two deliveries of one tier differ in no byte. The source and the notes close the last part:

```text
<!-- ruleset: tier T, N stems, part k of P -->

...the part's bodies...

<!-- ruleset: from S -->
<!-- note: ... -->
```

A tier packing into one part carries `<!-- ruleset: tier T, N stems -->` and the same trailer.

That run's readings on order and placement hold as properties. Parts reach context in the order
their hooks finish, which differed in each of the three runs and does not follow registration order.
Each header names its own place, which is how the sequence reads whatever the arrival order. Hook
context sits ahead of the user's prompt. An agent's own prompt sits in the system prompt, and
delivered rules ride in the message stream.

The cost is that arrival order carries no meaning. A reader who wants the parts in sequence reads
the headers.

## Every slot computes alone

Each of the ten part slots resolves the tier, composes it, packs it, and emits its own part or
nothing, without reading any other slot's output.

Every slot receives the same payload: that run compared the stdin of all ten hooks by sha256 and
found them byte-identical in every run. Given one payload and one corpus, every slot computes the
same composition and the same packing, and each keeps only the part matching its own `--part` index.
No slot signals another. Packing reads the sections and the budget alone, never a header or a note,
so a note one slot adds to its trailer cannot shift another slot's boundaries. A model
switch decides the same way: each slot compares `from_model` with `to_model` in the payload it holds
and delivers where the two map to different tiers, or where `from_model` is absent or unmapped.

The cost is ten small processes for each delivering event, run in parallel by the harness.

## Delivery follows the manifest's order

Composition follows the `order` list in `manifest.yaml`, and packing follows composition, so each
part carries rules that sit next to each other in that list.

The list is the corpus's own: every stem name lives in the corpus, and a corpus stating no order
composes its stems sorted. Grouping related stems in `order` makes a part read as one
theme, and a group placed at a boundary in the list arrives as a part of its own.

The cost is that moving a stem in `order` repacks every part from that stem onward, so those parts'
digests change even where no body did.

## One corpus, and a difference is one line

Every tier reads one set of bodies, and a tier states its difference rather than holding a copy.

`include: "*"` composes every stem under `default/`, and each stem a tier withholds is one line in
its `exclude` list. A tier that words a rule differently holds one file for that stem, and every
other stem still resolves to `default/`. A model gets a tier of its own with a directory named for
its identifier and one key under `tiers:`, which is why `claude-opus-4-8` needed no code change.

The cost lands on the copies. A body copied into a tier no longer follows edits to `default/`'s, and
the two drift until someone reconciles them. `check` catches the smaller slips: `stale-exclusion`
for an exclusion naming a stem no directory holds, `unreachable-body` for a copy no composition
reaches.

## Delivery fails open and says so

A hook that cannot read a tier, a manifest, or a body still exits 0, delivers what it can, and names
the failure in the text it delivers.

Delivery falls back to the `default` tier wherever a tier does not resolve, and where neither that
tier nor `default` composes, `_delivered` sends a header naming 0 stems with the reason in its
trailer. A hook that raises leaves that path, and `failure_output` in `hooks/deliver.py` answers in
the shape a delivery carries: the header `<!-- ruleset: delivery failed, 0 stems -->`, then text
telling the session to report the failure before doing anything else, naming whether the cause is a
file the hook could not read or write or a defect in this plugin, and carrying the command that runs
the hook by hand, then the trailer, `<!-- ruleset: from deliver.py -->` and one note holding the
cause. A cause that outruns the cap is clipped and ends in ` (clipped; the traceback is on the
hook's stderr)`. Only the `--part 1` slot prints it, and a later part that fails prints nothing on
stdout, so ten slots meeting one broken manifest report it once.

Slot 1 carries the rest of the work that must happen once: it scaffolds an absent corpus and writes
the delivery record and the session's tier. Slots 2 through P each write an emitted record,
`{"kind": "emitted", "session_id", "tier", "part", "parts", "stems", "digest"}`, the digest a sha256
of the part's text, into that writer's own file beside the first.

The cost is that a session can run with fewer rules than intended. The header is where that shows,
and `deliveries --session ID` and `delivery-check --session ID` are where it is checked after the
fact. `delivery-check` reads each delivery against its own writer's records, through
`read_records_for` in `lib/rulesets/audit.py`, and names a part composed and never emitted, a part
that disagrees on tier, and a part whose emitted digest disagrees with the sha256 of that part as
the tier composes now.

## Mechanism here, rules in the corpus

The plugin holds the resolver, the hooks, and the packer. The corpus holds every rule body, the
manifest that composes them, and the order they arrive in.

Every stem name lives in the corpus. The corpus root resolves from `--root`, then `RULESETS_ROOT`,
then `rulesets` under `CLAUDE_CONFIG_DIR` or `~/.claude`, so the rules can live in your own dotfiles
behind a symlink while the plugin updates on its own schedule.

The cost is that installing the plugin delivers nothing. The first delivering hook run, on
`SessionStart`, `SubagentStart`, or `PostModelSwitch`, scaffolds a legal and empty corpus, and the
rules are yours to write or to move in with `migrate-rules`.
