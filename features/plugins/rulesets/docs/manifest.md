# The rulesets directory and manifest

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
