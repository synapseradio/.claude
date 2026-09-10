# Installing model-scoped-rulesets

The plugin delivers a corpus of rules you own. Installing it gives you the mechanism and an empty
corpus; the rules stay yours to write or to move in.

## Before you start

Check that an interpreter can run the hooks:

```bash
python3 -c 'import sys, yaml; print(sys.version)'
```

Any of `python3.14`, `python3.13`, `python3.12`, or `python3` will do, as long as it reports 3.12 or
above and imports `yaml`. Where the one on your path cannot, name another in `RULESETS_PYTHON`.

## 1. Install the plugin

From the marketplace holding it:

```text
/plugin marketplace add <owner>/<repo>
/plugin install model-scoped-rulesets
```

For a local checkout, add the directory holding `.claude-plugin/marketplace.json` instead:

```text
/plugin marketplace add /path/to/checkout
/plugin install model-scoped-rulesets
```

## 2. Let the first session scaffold the corpus

Start a session. The `SessionStart` hook finds no corpus, writes an empty one at `~/.claude/rulesets`,
and says so in the context it delivers:

```text
<!-- ruleset: tier default, from ..., 0 stems -->
<!-- note: scaffolded an empty corpus at <home>/.claude/rulesets -->
```

Zero stems is correct. The corpus is legal and holds no rules yet.

To create it before that first session, or somewhere else:

```bash
resolve.py init                       # ~/.claude/rulesets
resolve.py init --root ~/dotfiles/rulesets
```

Where you keep the corpus elsewhere, either symlink `~/.claude/rulesets` at it or export
`RULESETS_ROOT`. The plugin follows the symlink and never writes over a root that exists.

## 3. Move your existing rules in

Claude Code loads every body under `~/.claude/rules/` into every context. Those bodies have to leave
that directory, or each one arrives twice: once from the harness, once from delivery.

Read what the move would do:

```bash
resolve.py migrate-rules --dry-run
```

Each line is one file. `move` means the body loads in every context today and goes to `default/`.
`stay` means the body carries `paths:` frontmatter, which scopes it to the files it names, so it
stays where the harness reads it. Then:

```bash
resolve.py migrate-rules
```

Nothing is edited. Each file is renamed, byte for byte, and the run records what it moved in
`<root>/.migration.jsonl`. `resolve.py migrate-rules --undo` puts the last run's moves back, and
refuses where a body changed since it moved.

## 4. Check the corpus and see what a model gets

```bash
resolve.py check                      # prints nothing and exits 0 on a legal corpus
resolve.py inspect --tier default     # each composed stem and the body it reads
```

Start a session and read the first comment of the delivered context: it names the tier, where that
tier came from, and how many stems it carried.

A first line reading `<!-- ruleset: delivery failed, from deliver.py, 0 stems -->` means the hook
ran and could not deliver. The note under it names the cause, and the text after it says whether
the cause is a file the hook could not read or a defect in the plugin. The session has no user
rules until a new one starts after the repair. The hook exits 0 either way, so a session is never
blocked, and it never starts with no rules and no word of it.

```bash
resolve.py deliveries --session <session_id>
resolve.py delivery-check --session <session_id>
```

## 5. Give one model its own rules

To override one body for one family, copy it into that tier and edit the copy:

```bash
cp ~/.claude/rulesets/default/some-rule.md ~/.claude/rulesets/haiku/some-rule.md
```

The manifest needs no change: `include: "*"` already composes that stem for every tier. Delete the
copy and the stem resolves back to `default/`.

To give one model identifier its own tier, create a directory named for the identifier and add a key
for it under `tiers:` in `manifest.yaml`. A lookup matches that tier ahead of the family, so
`models.yaml` needs no entry.

## If your settings file already ran these hooks

The plugin wires `SessionStart`, `SubagentStart`, `PostModelSwitch`, `PreToolUse` on `Agent`, and
`InstructionsLoaded`. Claude Code does not deduplicate hooks across sources, so remove your own
entries for those events, or one context receives the same ruleset twice.

## Uninstalling

```text
/plugin uninstall model-scoped-rulesets
```

The corpus is yours and stays where it is. Nothing delivers it after that, so move the bodies you
want back under `~/.claude/rules/` first, or run `resolve.py migrate-rules --undo` while the plugin
is still installed.
