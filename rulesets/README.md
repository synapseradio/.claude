# rulesets

The rules this repository delivers to Claude Code sessions and delegates. This page is for editing
them. The plugin's [config page](../features/plugins/rulesets/docs/config.md) covers how it
composes them, its [delivery page](../features/plugins/rulesets/docs/delivery.md) how it delivers
them, and its [commands page](../features/plugins/rulesets/docs/commands.md) every command named
below.

The commands below run from the repository root. `$CLI` stands for
`python3.14 features/plugins/rulesets/lib/rulesets/cli.py`.

## Where rules live

```text
rulesets/
  config.yaml      which rules each context receives
  rules/           the pool: one file per rule or variant
  -render/         generated renders, written by `render`
```

- A rule is `rules/<name>.md`, its default form. It may be empty.
- A variant is `rules/<name>@<variant>.md`, for example `writing-prose@haiku.md`, and needs the
  default form beside it.
- A rule file carries its text and no marker line. Delivery writes `<!-- rule: <name> -->` and a
  blank line before each rule's body, and those bytes count toward the 9,000-character budget of a
  delivered part. A rule file and its marker together come to 9,000 characters or fewer.
- `config.yaml` decides who receives what. `defaults` gives every context the `core` set, and each
  condition block, such as `kind session:` or `agent critic:`, includes or excludes rules for the
  contexts its condition matches, or sets a variant for them. A new rule file reaches every main
  session through `include: all.*` under `kind session:`, with no config edit. To keep a rule from
  some contexts, add it under `exclude:` in a block.

The folder also holds the directories of the earlier tier layout, `default/`, `fable/`, `opus/`,
`sonnet/`, `haiku/`, `claude-opus-4-8/`, and `renders/`. The engine reads none of them, and `check`
prints a stray-directory warning for each.

Find which line decided a rule in a context:

```bash
$CLI explain writing-prose --model haiku --root rulesets
```

## Editing a rule

Edit the rule file, or edit its section in a render and write the change back.

To edit a rule file directly, change `rules/<name>.md`, then refresh the render tree:

```bash
$CLI render --root rulesets
```

To edit through a render, open one of the files in `rulesets/-render/`. `defaults.md` holds the rules
the base context receives, `all.md` holds the whole pool at default forms, and a
`<render>+<rule>@<variant>.md` holds the same rules with one variant set. Render writes a marker line
before each rule, `<!-- rule: <name> -->`, or `<!-- rule: <name> variant: <variant> -->` for a
variant. Edit the text under a marker, keep the marker lines, and write it back:

```bash
$CLI split rulesets/-render/defaults.md --root rulesets
```

`split` routes each section by its marker, writes the text back to the rule file unchanged, and
prints `wrote <path>` for each rule file whose section you changed. It touches no other file. It
refuses a file with no marker, a file with text before the first marker, a marker naming a rule or
variant the pool does not hold, or a marker that appears twice. It writes nothing then, names the
cause, and exits 1. A rule file that opens on a marker line of its own gets a second marker from
delivery and from `render`, and `split` then refuses the render for the repeated marker; the marker
belongs to delivery and to `render`, so a rule file carries none.

After a split, run `render` again. The edited rule appears in every other render that holds it, and
until you render, those renders differ from the pool. Commit the files `render` writes together
with the rule change.

## The pre-push gate

The `sync-agent-configs` job in `lefthook.yml` runs on a push from `main`. Among its steps it runs
two commands against `rulesets/`:

```bash
$CLI check --root rulesets
$CLI render --check --root rulesets
```

`check` fails the push on an error: a variant with no default form, a reference to a name nothing
declares, a ruleset cycle, a condition that tests anything but a fact, a rule file longer than 9,000
characters with its marker. Warnings print and do not fail it. `render --check` fails the push when a
file under `-render/` differs from what `render` would write, and names each such file. The gate's
message says what to do: run `render` without `--check`, commit the renders it writes, and push
again.

The same job regenerates and checks the pi and opencode configs, which read each rule's default form
from the pool. A variant never reaches them.

Run both commands yourself before pushing to see what the gate will say.

## What stays out of the pool

`epistemic-marks` ships in its own plugin, `features/plugins/epistemic-marks`. That plugin delivers
its rule text itself, through its own `SessionStart` and `SubagentStart` hooks, from
`rule-text/epistemic-marks.md`. It has no file in `rules/` and no line in the config, so a rule
added to the pool under that name would be a second copy.
