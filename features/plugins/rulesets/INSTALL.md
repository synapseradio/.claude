# Installing rulesets

The plugin delivers rules you own. Installing it gives you the mechanism and an empty rulesets
directory; the rules stay yours to write or to move in.

## Before you start

The hooks and the command line need Python 3.14 or later with PyYAML. Check the interpreter:

```bash
python3.14 --version
```

The hook launcher tries `python3.14`, `python3.15`, and `python3`, and runs the first that reports
3.14 or later and imports `yaml`. Where none does, a session starts without the plugin's rules and
shows you a message naming the requirement. To name a particular interpreter, set `RULESETS_PYTHON`
to its path or name.

Install PyYAML for that interpreter, for example with `python3.14 -m pip install pyyaml`, or with
your usual Python package tool.

## 1. Install the plugin

The repository's marketplace is `claude-root`. Add it, then install the plugin from it:

```bash
claude plugin marketplace add synapseradio/.claude
claude plugin install rulesets@claude-root
```

For a local checkout, add the directory that holds `.claude-plugin/marketplace.json`:

```bash
claude plugin marketplace add /path/to/checkout
claude plugin install rulesets@claude-root
```

## 2. Let the first session scaffold the directory

Start a session. Where `~/.claude/rulesets` does not exist, the first delivery of the session
creates it, with an empty `rules/` pool and a manifest that declares nothing. It delivers no rules,
and it shows you a message saying where it scaffolded.

An empty pool is legal. A `defaults` list that names nothing delivers nothing, so write your rules
first.

## 3. Add a rule and a manifest line

Write a rule as a markdown file in the pool, then reference it from the manifest. A rule file holds
the rule's text and no marker line; delivery writes the marker.

```text
~/.claude/rulesets/rules/voice.md
```

```yaml
defaults: ["all:*"]
```

`all:*` spreads every rule in the pool to every context. See [the manifest page](docs/manifest.md) for
variants, blocks, and flags.

If you hold rules already, `adopt` maps a folder of rule files, or a tier corpus, into a new
rulesets directory and compares what the source delivers with what the new directory delivers:

```bash
python3.14 <plugin directory>/lib/rulesets/cli.py adopt --from ~/old-rules --out ~/new-rulesets
```

`--out` must be an empty directory. Adopt leaves the source as it was.

## 4. Run the first check

`check` reads a rulesets directory and prints every error and warning in one run. It exits 1 only
when it finds an error.

```bash
python3.14 <plugin directory>/lib/rulesets/cli.py check --root ~/.claude/rulesets
```

A clean directory prints nothing and exits 0. A line reads
`<file>:<line>: warning [kind] ...` or the same with `error`. Fix every error before trusting a
delivery: delivery withholds a rule whose file carries an error, and it skips a reference to a name
nothing declares and a block whose condition is invalid or names an undeclared model or flag.

## 5. Confirm a delivery happened

Each delivery appends one record to the session's log, under the configuration directory
(`~/.claude` unless `CLAUDE_CONFIG_DIR` is set):

```text
.tmp/rulesets-engine/audit/<session id>/deliveries.jsonl
```

The directory name is the session identifier with every character other than letters, digits, `-`,
and `_` removed; list `.tmp/rulesets-engine/audit/` to find yours. Each record names the session,
the delegate where there is one, the scope (`session`, `delegate`, or `switch`), the context's model
with its source, each rule delivered with its variant and a digest of its text, and anything the
delivery skipped, withheld, or showed.

To read the record as one line per delivery:

```bash
python3.14 <plugin directory>/lib/rulesets/cli.py deliveries --session <session id>
```

For a session that received two rules on an opus model, the line reads, tab-separated:

```text
session  opus  harness-reported  2  -
```

The columns are the scope, the model, the model's source, the rule count, the flags set (or `-`),
and, for a delegate, its identifier. A session with no record prints nothing and exits 0, which
means no delivery reached it: check that the plugin is installed and enabled, then that
Python 3.14 with PyYAML is available.

To compare a record with what the manifest and the pool compose now:

```bash
python3.14 <plugin directory>/lib/rulesets/cli.py delivery-check --session <session id>
```

It prints nothing and exits 0 where every delivery matches, and exits 1 after printing a line for
each difference.

## If your settings file already runs these hooks

The plugin registers `SessionStart`, `SubagentStart`, `PostModelSwitch`, `PreToolUse` on `Agent`,
`InstructionsLoaded`, and `SessionEnd`. It does not look for other hooks that deliver rules. Where
your own settings file runs one of that kind on these events, a context can receive its rules twice,
so remove your own entries.

## Uninstalling

```bash
claude plugin uninstall rulesets@claude-root
```

The rulesets directory is yours and stays where it is. Nothing delivers it after that.
