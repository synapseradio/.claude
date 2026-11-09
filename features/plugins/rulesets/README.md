# rulesets

Compose the rules each Claude Code session and delegate receives, from one pool of rule files and
one manifest. A rule is a text file. The manifest says which rules reach which context: every
context, one model, one agent, or any session where you set a flag. The plugin delivers the result
through hooks and records what it delivered, so you can read back what any context received.

This page covers what the plugin does and how to drive it. [INSTALL.md](INSTALL.md) covers installing
it.

## What it delivers, and to whom

| Context | When it receives rules | Hook |
| --- | --- | --- |
| The main session | at start, resume, clear, and compaction | `SessionStart` |
| A delegate | when it starts | `SubagentStart` |
| The main session, after a model switch | when the switch composes different rules | `PostModelSwitch` |

Each delivery carries the whole composition for that context, never a difference. The rules arrive
in name order. Before each rule's body, delivery writes the line `<!-- rule: <name> -->` and a blank
line, so a rule file carries no marker line of its own. A rule at a variant arrives under the same
marker, with the variant's text and the variant left unnamed. The same composition always yields the
same bytes.

A delivery splits into parts. One hook entry carries one part, and a part holds whole rule bodies up
to 9,000 characters, counting each rule's marker and blank line. A rule never splits across parts.
A delivery carries at most 10 parts; a rule that would need an eleventh part is left out, and
`check` warns about the context. A rule whose body and marker pass 9,000 characters on their own is
a `check` error, and delivery withholds it.

A delegate composes from its own facts: its model, its agent type, and the flags that hold. The
delegate's model comes from the first of these that names one: the model the caller named for the
spawn, the agent definition's pin, the `CLAUDE_CODE_SUBAGENT_MODEL` variable, and the parent
session's recorded model. A haiku delegate under an opus session receives the haiku composition when
the spawn names haiku, and the session keeps the opus one.

Several delegates of one agent type spawned in one message can each name a different model. The
harness tells a starting delegate nothing that identifies its spawn, so each delegate takes the
oldest spawn of its type in that message that no earlier delegate took, and keeps it when resumed.
The harness does not promise that delegates start in the order they were spawned; a delegate that
starts out of order takes another delegate's model, and no notice reports the swap. A delegate that
finds every such spawn taken takes the model they all name, or, where they name different models,
the next source above, with a notice of ambiguity in its delivery record.

After a model switch, the plugin composes again for the new model. Where the new model composes the
same rules at the same variants as the rules last delivered, it delivers nothing. Where it composes
different rules, it delivers them, and the earlier rules remain in the conversation above them; the
plugin cannot retract text it already delivered.

Three further hooks deliver nothing. A `PreToolUse` hook on the `Agent` tool records each spawn and
the model its caller names, if any. An `InstructionsLoaded` hook records each instruction file the harness
loaded. A `SessionEnd` hook ends the session's toggles. The records feed the checks below.

A delivery can skip a reference, withhold a rule, leave a rule out, or reach no rule, and each
draws a notice. At session start, the plugin shows the notices to you as a message and never puts
them into the agent's context. A delegate's start and a model switch show no message; their
notices sit in the delivery record, under `notices`. A session start that raises nothing shows no
message.

## Words used here

- A **rule** is one named text.
- A **variant** is a named alternative text of one rule. A rule's **default form** is its text
  under no variant.
- The **pool** is the `rules/` folder that holds every rule file.
- A **ruleset** is a named list of references.
- A **reference** names a rule, a rule at a variant, or the spread of a ruleset, and may carry a
  remove sign.
- A **block** is a condition paired with one list of references. It applies in each context where
  the condition holds.
- A **flag** is a declared name that a launch or a toggle sets.
- A **model** is a declared Claude model name, such as `opus`.
- A **context** is the main session or one delegate, at one delivery.
- A **delivery** is one context receiving its rules. A **part** is one group of whole rule bodies
  that one hook entry carries.

## The rulesets directory

The plugin reads one rulesets directory, at `~/.claude/rulesets/`. It reads no rulesets directory
inside a project, and it leaves a project's `.claude/rules` folder and `~/.claude/rules` to the
harness. Where `CLAUDE_CONFIG_DIR` is set, the directory is `rulesets/` under that path instead.

```text
rulesets/
  manifest.yaml        which rules each context receives
  rules/               the pool: one file per rule or variant
    voice.md           the default form of the rule `voice`
    voice@terse.md     the variant `terse` of `voice`
  -render/             generated renders, written by `render`
  references/          files a rule may cite, kept with the directory
```

A rule's name is its file name up to any `@`. Every rule has a default form, `name.md`, which may be
empty. A variant file `name@variant.md` without a default form is a `check` error, and delivery
withholds that rule. A file in the pool delivers nothing by being there: a rule reaches a context
only through a reference in the manifest. A rule file carries text only, with no marker line, and
metadata that carries a condition is a `check` error. The engine never reads `-render/` as rules, and
a directory beside the pool that holds no rule draws a `check` warning.

### The manifest

`manifest.yaml` holds these keys. Write every list entry as a quoted string.

```yaml
models: ["opus", "haiku"]
flags: ["strict"]
defaults: ["all:*"]
rulesets:
  review: ["security-pass", "voice@terse"]
when:
  - "model haiku": ["-security-pass"]
  - "flag strict": ["review:*"]
```

- `models` declares the model names a condition may test. A declared name `n` claims the identifier
  `claude-n` and every identifier that continues it with `-` or `[`, so `opus` claims
  `claude-opus-4-8` and `claude-opus-5-5[1m]`. Where two declared names claim one identifier, the
  longer wins. A model that no declared name claims tests false in every `model` condition.
- `flags` declares the flag names. A launch sets flags through the `RULESETS_FLAGS` environment
  variable, a comma-separated list, as in `RULESETS_FLAGS=strict claude`. A flag the manifest does
  not declare is dropped, with a notice.
- `defaults` is the list that applies in every context, at the lowest precedence.
- `rulesets` names reusable lists.
- `when` is a list of blocks. Each item maps one condition to one list.

A reference takes one of these forms, and a leading `-` removes what the form names:

| Written | Names |
| --- | --- |
| `voice` or `rules:voice` | the rule `voice`, at no chosen variant |
| `voice@terse` | the rule `voice`, set to the variant `terse` |
| `review:*` | every entry of the ruleset `review` |
| `*` or `all:*` | every rule in the pool, each at its default form |

`-voice@terse` strikes the variant and leaves the rule's inclusion as it was.

These ruleset names are reserved: `defaults`, `all`, `rules`, and `none`. `none` holds no rule.

A condition combines tests of these facts with `and`, `or`, `not`, and parentheses: `model <name>`,
`agent <name>`, `kind session|delegate`, `tools <Tool>`, `flag <name>`, and `session <id>`. A
condition tests facts only. A test of a project, a file, or an environment variable is a `check`
error, and the block applies nowhere. A block that names an undeclared model or flag is skipped,
with a notice.

Where statements disagree about a rule, the one at the highest position decides. Position follows
these orderings, each settling only the ties the earlier ones leave:

1. A toggle you set in the session beats the manifest.
2. A block that tests a higher-ranked fact beats a lower one. From lowest to highest the ranks are
   `defaults`, model, agent or kind or tools, flag, session.
3. A statement that names a rule beats one that reaches it through a ruleset.
4. A remove beats an add.

`explain` shows which line decided a rule in a given context.

## Commands

Each command runs through the plugin's `cli.py`. In the examples, `$CLI` stands for
`python3.14 <plugin directory>/lib/rulesets/cli.py`, and `--root` names the rulesets directory.
Where a command accepts `--root` and you omit it, the command reads `~/.claude/rulesets`; `check`
requires it.

| Command | What it does |
| --- | --- |
| `check` | Prints every error and warning of a rulesets directory. Exits 1 on an error only. |
| `explain` | Prints which manifest lines decided one rule in one named context. |
| `render` | Writes the composed text one context receives, or the whole render tree. |
| `render --check` | Writes nothing. Exits 1 where the render tree on disk differs from what `render` writes. |
| `split` | Writes each section of an edited render back to the rule file it came from. |
| `eject` | Writes the base context as one plain file per rule. |
| `adopt` | Maps a tier corpus or a plain rules folder to a new rulesets directory and compares what the two deliver. |
| `compare` | Compares what a source delivers with what a rulesets directory delivers. |
| `deliveries` | Prints one line for each delivery that reached a context in a session. |
| `delivery-check` | Recomposes a session's deliveries and prints each difference. |
| `load-check` | Prints each file the harness loaded that a rule of the pool is named for. |
| `toggle` | Changes what the delegates a session starts from now on receive. |

A context is named by its facts: `--model`, `--agent`, `--kind`, `--tools`, and `--flag`, each
optional. A fact you leave out is absent, except flags, which are unset.

### check

```bash
$CLI check --root ~/.claude/rulesets
```

Reports every error and every warning in one run, each with its file and line. Errors include a
variant with no default form, a ruleset cycle, a reference to a name nothing declares, a condition
that tests anything but a fact, a rule file longer than 9,000 characters with its marker, frontmatter
that carries a condition, conflicting variants set by blocks that can both apply, and an unknown
top-level key. Warnings include a rule that no add includes, a rule whose text names another rule
(by its name in backticks, its file name, a link to its file, or the phrase "rule name" or "the name
rule"; a bare word is no mention), a stray directory, a file path a rule cites that the directory
does not hold (a path with a `<placeholder>` segment is no citation), a context whose rules need
more parts than a delivery carries, and a rule file that opens on a marker for another rule or
another form of its own. A warning never fails the run. A clean directory prints nothing.

### explain

```bash
$CLI explain voice --model haiku --flag strict
```

Prints two attributes of the rule, inclusion and variant. Each opens with the winning line and then
lists the lines it beat, with the file and line of each. It exits 1 and names the rule where the pool
holds none.

### render

```bash
$CLI render --model haiku --out haiku.md --root ~/.claude/rulesets
```

Writes the rules that context receives, sorted by name, each under a marker line
`<!-- rule: voice -->`, or `<!-- rule: voice variant: terse -->` for a variant. A withheld rule is
left out. A render is for reading and editing; its text is not the text delivery sends, which writes
a blank line after each marker.

With no `--out`, `render` ignores any context named and replaces the contents of `-render/` with a
tree: `defaults.md`, `all.md`, one `<ruleset>.md` for each declared ruleset, and a
`<render>+<rule>@<variant>.md` for each variant a manifest add names.

```bash
$CLI render --root ~/.claude/rulesets
```

### render --check

```bash
$CLI render --check --root ~/.claude/rulesets
```

Writes nothing, names each file under `-render/` that differs from what `render` would write, and
exits 1 if any does.

### split

```bash
$CLI split ~/.claude/rulesets/-render/defaults.md
```

Reads the markers in a rendered file and writes each edited section back to its file in the pool:
`name.md` where the marker names no variant, `name@variant.md` where it does. Each section's text
goes back unchanged. It changes only the files whose sections you edited, and it prints
`wrote <path>` for each. It refuses a file with no marker, a file with text before the first marker,
a marker that names a rule or variant the pool does not hold, or a marker that appears twice. It
then writes nothing, names the cause, and exits 1.

### eject

```bash
$CLI eject --out ~/rules-plain
```

Writes one `<rule>.md` for each rule the `defaults` list gives, at its default form, and prints
`wrote <path>` for each. It prints each block and each variant that plain files cannot carry, with
file and line, and changes no source file.

### adopt

```bash
$CLI adopt --from ~/old-rules --out ~/new-rulesets
```

Maps a folder of rule files, or a tier corpus, into a new rulesets directory at `--out`. It removes
a source file's opening marker line for its own rule, and the blank line after it, because delivery
writes both. It leaves the source as it was and refuses, with exit
2, an output directory that is the source, lies inside it, or already holds files. It then compares
what the source delivers with what the new directory delivers, for each context in a matrix, and
exits 1 where any context differs. `--expect <identifier>` names a model identifier whose
differences are expected; give it once for each such identifier. It also adds that identifier to the
matrix.

### compare

```bash
$CLI compare ~/old-rules ~/new-rulesets
```

Runs the same comparison on its own, so a rulesets directory edited after adoption is checked the
same way. The matrix crosses no model, each tier the source names, each model identifier a delivery
record names, and each `--expect` identifier with no agent and with each agent definition under the
configuration directory's `agents/` folder. The command names each context that differs and the
first rule and variant where it differs, and ends with `compared <n> contexts`.

### deliveries

```bash
$CLI deliveries --session demo-1
```

Prints one tab-separated line for each delivery that reached a context, in file order: the scope
(`session`, `delegate`, or `switch`), the model, the model's source, the rule count, the flags set
(or `-`), and the delegate identifier for a delegate. For example:
`session  opus  harness-reported  2  -`. Where several model switches share one prompt, only the
last counts.

Two companions read the same records. `delivery-check --session <id>` recomposes each counted
delivery against the manifest and the pool as they stand now and prints a line for each rule
composed but not delivered, delivered but not composed, or delivered at a different variant, and for
each later part never emitted or emitted with text that differs from what composes now. It exits 1
where it prints any line. `load-check --session <id>` prints each file the harness loaded that is
named for a rule of the pool, so a rule still auto-loading from a rules folder shows up. A file
named `CLAUDE.md` is exempt, and the command exits 1 where it prints any line.

### toggle

```text
/rulesets:toggle flag strict
```

Changes what the delegates this session starts from now on receive. The actions are `all` (every
rule in the pool), `none` (no rule), `flag NAME`, `unflag NAME`, and `clear` (end every toggle of
the session). The later of `all` and `none` replaces the earlier. A flag name must be declared in
the manifest; an undeclared name exits 1, names the flag, and writes nothing.

A toggle reaches only delegates that start after it. It leaves the main session's rules and the
rules of any running delegate as they are. Toggles survive compaction. A clear or a resume of the
session ends them, and so does the session's close.

The same action runs from a shell as `$CLI toggle --session <id> flag strict`.

## Where records live

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

## What it leaves alone

- **Forks.** A forked session and a fork subagent already carry the parent's rules in the
  conversation they inherit, so the plugin gives them nothing, records nothing for them, and shows
  no notice.
- **The harness's own rules.** A project's `.claude/rules` folder and `~/.claude/rules` load as they
  would without the plugin. A rule kept both there and in the pool reaches a context twice, so move
  it into the pool and run `load-check` to confirm nothing still auto-loads it.
- **Agent definitions and spawn prompts.** Delivery reads an agent definition for its model pin and
  its tools, and writes into neither the definition nor the prompt.
- **Text already delivered.** No toggle and no model switch retracts a rule already in a context.
- **A session that cannot start the engine.** Where no interpreter reports Python 3.14 with PyYAML,
  the session starts without the plugin's rules and you see a message naming the requirement.

Where the manifest is missing or does not parse, delivery sends the default form of every rule in
the pool, with a notice. Where no rulesets directory exists, the first delivery creates an empty one
and says where, at session start.
