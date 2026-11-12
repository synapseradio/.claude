# Commands

Each command runs through the plugin's `cli.py`. In the examples, `$CLI` stands for
`python3.15 <plugin directory>/lib/rulesets/cli.py`, and `--root` names the rulesets directory.
Where a command accepts `--root` and you omit it, the command reads `~/.claude/rulesets`; `check`
requires it.

| Command | What it does |
| --- | --- |
| `check` | Prints every error and warning of a rulesets directory. Exits 1 on an error only. |
| `explain` | Prints which config lines decided one rule in one named context. |
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

## check

```bash
$CLI check --root ~/.claude/rulesets
```

Reports every error and every warning in one run, each with its file and line. Errors include a
variant with no default form, a cycle among sets, a reference to a name nothing declares, a condition
that tests anything but a fact, a rule file longer than 9,000 characters with its marker, frontmatter
that carries a condition, conflicting variants set by blocks that can both apply, a condition written twice as a key at one
level, a config written in an older layout, and a config file YAML cannot read, each with the form
to write instead. A directory that holds an older config file and no `config.yaml` is an error
naming `config.yaml`. Every message quotes a reference as the config writes it, as
`code.resolving-input` or `all.*`. Warnings include a rule that no add includes, a rule whose text names another rule
(by its name in backticks, its file name, a link to its file, or the phrase "rule name" or "the name
rule"; a bare word is no mention), a stray directory, a file path a rule cites that the directory
does not hold (a path with a `<placeholder>` segment is no citation), a context whose rules need
more parts than a delivery carries, and a rule file that opens on a marker for another rule or
another form of its own. A warning never fails the run. A clean directory prints nothing.

## explain

```bash
$CLI explain voice --model haiku --flag strict
```

Prints two attributes of the rule, inclusion and variant. Each opens with the winning line and then
lists the lines it beat, with the file and line of each. A line gives the block's combined
condition, or `defaults`, and the reference as the config writes it, as `exclude bash.shell-scripts`. It exits 1 and names the rule where the pool
holds none.

## render

```bash
$CLI render --model haiku --out haiku.md --root ~/.claude/rulesets
```

Writes the rules that context receives, sorted by name, each under a marker line
`<!-- rule: voice -->`, or `<!-- rule: voice variant: terse -->` for a variant. A withheld rule is
left out. A render is for reading and editing; its text is not the text delivery sends, which writes
a blank line after each marker.

With no `--out`, `render` ignores any context named and replaces the contents of `-render/` with a
tree: `defaults.md`, `all.md`, one `<set>.md` for each declared set, and a
`<render>+<rule>@<variant>.md` for each variant an `include` in the config names.

```bash
$CLI render --root ~/.claude/rulesets
```

## render --check

```bash
$CLI render --check --root ~/.claude/rulesets
```

Writes nothing, names each file under `-render/` that differs from what `render` would write, and
exits 1 if any does.

## split

```bash
$CLI split ~/.claude/rulesets/-render/defaults.md
```

Reads the markers in a rendered file and writes each edited section back to its file in the pool:
`name.md` where the marker names no variant, `name@variant.md` where it does. Each section's text
goes back unchanged. It changes only the files whose sections you edited, and it prints
`wrote <path>` for each. It refuses a file with no marker, a file with text before the first marker,
a marker that names a rule or variant the pool does not hold, or a marker that appears twice. It
then writes nothing, names the cause, and exits 1.

## eject

```bash
$CLI eject --out ~/rules-plain
```

Writes one `<rule>.md` for each rule the `defaults` list gives, at its default form, and prints
`wrote <path>` for each. It prints each block and each variant that plain files cannot carry, with
file and line, and changes no source file.

## adopt

```bash
$CLI adopt --from ~/old-rules --out ~/new-rulesets
```

Maps a folder of rule files, or a tier corpus, into a new rulesets directory at `--out`, with a
`config.yaml` in the layout above the blocks it maps. It removes
a source file's opening marker line for its own rule, and the blank line after it, because delivery
writes both. It leaves the source as it was and refuses, with exit
2, an output directory that is the source, lies inside it, or already holds files. It then compares
what the source delivers with what the new directory delivers, for each context in a matrix, and
exits 1 where any context differs. `--expect <identifier>` names a model identifier whose
differences are expected; give it once for each such identifier. It also adds that identifier to the
matrix.

## compare

```bash
$CLI compare ~/old-rules ~/new-rulesets
```

Runs the same comparison on its own, so a rulesets directory edited after adoption is checked the
same way. The matrix crosses no model, each tier the source names, each model identifier a delivery
record names, and each `--expect` identifier with no agent and with each agent definition under the
configuration directory's `agents/` folder. The command names each context that differs and the
first rule and variant where it differs, and ends with `compared <n> contexts`.

## deliveries

```bash
$CLI deliveries --session demo-1
```

Prints one tab-separated line for each delivery that reached a context, in file order: the scope
(`session`, `delegate`, or `switch`), the model, the model's source, the rule count, the flags set
(or `-`), and the delegate identifier for a delegate. For example:
`session  opus  harness-reported  2  -`. Where several model switches share one prompt, only the
last counts.

Two companions read the same records. `delivery-check --session <id>` recomposes each counted
delivery against the config and the pool as they stand now and prints a line for each rule
composed but not delivered, delivered but not composed, or delivered at a different variant, and for
each later part never emitted or emitted with text that differs from what composes now. It exits 1
where it prints any line. `load-check --session <id>` prints each file the harness loaded that is
named for a rule of the pool, so a rule still auto-loading from a rules folder shows up. A file
named `CLAUDE.md` is exempt, and the command exits 1 where it prints any line.

## toggle

```text
/rulesets:rulesets flag strict
```

Changes what the delegates this session starts from now on receive. Type the action after
`/rulesets:rulesets`, or ask for it in words, such as "turn on strict for my delegates"; the model
runs the command for the current session and reports the result in one sentence. The actions are `all` (every
rule in the pool), `none` (no rule), `flag NAME`, `unflag NAME`, and `clear` (end every toggle of
the session). The later of `all` and `none` replaces the earlier. A flag name must be declared in
the config; an undeclared name exits 1, names the flag, and writes nothing.

A toggle reaches only delegates that start after it. It leaves the main session's rules and the
rules of any running delegate as they are. Toggles survive compaction. A clear or a resume of the
session ends them, and so does the session's close.

The same action runs from a shell as `$CLI toggle --session <id> flag strict`.
