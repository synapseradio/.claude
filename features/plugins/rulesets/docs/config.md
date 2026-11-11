# The rulesets directory and config

## Words used here

- A **rule** is one named text.
- A **variant** is a named alternative text of one rule. A rule's **default form** is its text
  under no variant.
- The **pool** is the `rules/` folder that holds every rule file.
- A **set** is a named list of references, declared under `sets`. Check and explain messages call
  it a ruleset.
- A **reference** names a rule, a rule at a variant, or every entry of a set. It sits under
  `include` or `exclude`.
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
  config.yaml          which rules each context receives
  rules/               the pool: one file per rule or variant
    voice.md           the default form of the rule `voice`
    voice@terse.md     the variant `terse` of `voice`
  -render/             generated renders, written by `render`
  references/          files a rule may cite, kept with the directory
```

A rule's name is its file name up to any `@`, and holds no `.`. Every rule has a default form,
`name.md`, which may be empty. A variant file `name@variant.md` without a default form is a `check`
error, and delivery withholds that rule. A file in the pool delivers nothing by being there: a rule
reaches a context only through a reference in the config. A rule file carries text only, with no
marker line, and metadata that carries a condition is a `check` error. The engine never reads
`-render/` as rules, and a directory beside the pool that holds no rule draws a `check` warning.

The engine reads `config.yaml` and no other file for the config. A directory that holds an older
config file and no `config.yaml` draws a `check` error naming `config.yaml`, and a session start
shows a notice saying the same.

## The config

`config.yaml` is a YAML mapping. This one uses every reserved key:

```yaml
models: opus haiku
flags: strict
defaults: all.*
sets:
  review: security-pass voice@terse
model haiku:
  exclude: security-pass
flag strict:
  include: review.*
agent critic thinkies:
  not model haiku:
    include: voice
```

- `models` declares the model names a condition may test. A declared name `n` claims the identifier
  `claude-n` and every identifier that continues it with `-` or `[`, so `opus` claims
  `claude-opus-4-8` and `claude-opus-5-5[1m]`. Where two declared names claim one identifier, the
  longer wins. A model that no declared name claims tests false in every `model` condition.
- `flags` declares the flag names. A launch sets flags through the `RULESETS_FLAGS` environment
  variable, a comma-separated list, as in `RULESETS_FLAGS=strict claude`. A flag the config does
  not declare is dropped, with a notice.
- `defaults` is the list that applies in every context, at the lowest precedence.
- `sets` names reusable lists. A set's name holds no `.`, and `defaults`, `all`, `rules`, and `none`
  are reserved.
- Every other top-level key is a block, and the key is its condition.

Each of `models`, `flags`, `defaults`, and `sets` appears at most once.

### Lists

A list is words separated by whitespace, across as many lines as it needs, with no quotes,
brackets, or dashes. Each word is read as written, so `models: 4.5` declares the name `4.5`. Check
and explain cite each word at its own line.

```yaml
models: opus sonnet haiku
sets:
  review: security-pass report-format
    review-method voice@terse
```

`defaults` and each set take either words, which it includes, or a mapping of `include` and
`exclude`, which together form its one list:

```yaml
defaults:
  include: all.*
  exclude: bash.shell-scripts
sets:
  bash: shell-scripts
```

### Blocks

A block's value is a mapping of these keys:

- `include` and `exclude` hold the block's one list.
- `then` holds a separate list, written as a block, that applies under the same condition.
- Any other key is a nested block. Its condition is the enclosing condition joined to its own with
  `and`, so the nested block applies only where both hold, and its list stands apart from the
  enclosing one.

```yaml
models: opus haiku
sets:
  planning: writing-plans
agent Plan:
  not model haiku:
    include: planning.*
```

This gives `planning.*` to a Plan delegate on any model but haiku, as the condition
`agent Plan and not model haiku`.

A block that holds none of these keys is a `check` error, and so is a block whose words sit
directly under the condition with no `include`.

An `exclude` beats an `include` of the same rule within one list, so a block that includes
`prose.writing-prose@haiku` and excludes `prose.writing-prose` in one list sets no variant, and a
rule that another block includes arrives at its default form. Written under `then`, the exclude
forms a list of its own, and the variant the first list sets stays:

```yaml
models: haiku
sets:
  prose: writing-prose
model haiku:
  include: prose.writing-prose@haiku
  then:
    exclude: prose.writing-prose
```

A condition written twice as a key at one level draws a `check` error naming both lines, and
delivery skips both blocks. Use `then` to give one condition a second list.

### References

A reference takes one of these forms:

| Written | Names |
| --- | --- |
| `voice` | the rule `voice`, at no chosen variant |
| `voice@terse` | the rule `voice`, set to the variant `terse` |
| `review.voice` | the rule `voice`, which the set `review` must hold |
| `review.voice@terse` | the same rule, set to the variant `terse` |
| `review.*` | every entry of the set `review` |
| `all.*` | every rule in the pool, each at its default form |

`all.rule` and `rules.rule` name a rule of the pool, `rules.*` equals `all.*`, `none.*` holds no
rule, and `defaults.*` holds the entries of `defaults`.

Removal is `exclude`, never a sign on the word. `exclude: voice@terse` strikes the variant and
leaves the rule's inclusion as it was. A word in an older form, such as a leading `-`, a bare `*`,
or a set written with a colon, draws a `check` error that names the form to write instead.

### Conditions

A condition combines fact tests with `and`, `or`, `not`, and parentheses. A fact test is a fact kind
followed by one or more values:

| Test | Holds where |
| --- | --- |
| `model <name>...` | the context's model is one of the declared names |
| `agent <name>...` | the delegate is one of these agent types |
| `kind session`, `kind delegate`, `kind any` | the context is a session, a delegate, or either |
| `tools <Tool>...` | the delegate holds one of these tools |
| `flag <name>...` | one of these flags is set |
| `session <id>...` | the session is one of these identifiers |

Several values after one kind hold where any of them holds: `agent critic thinkies` reads as
`agent critic or agent thinkies`, and `not model haiku sonnet` holds only on a model that is
neither. `not` binds tighter than `and`, and `and` tighter than `or`. `kind any` holds in every
session and delegate, and a block that tests it takes the rank of `kind`.

A condition tests facts only. A test of a project, a file, or an environment variable is a `check`
error, and the block applies nowhere. A block that names an undeclared model or flag is a `check`
error, and delivery skips it with a notice.

### Which statement wins

Where statements disagree about a rule, the one at the highest position decides. Position follows
these orderings, each settling only the ties the earlier ones leave:

1. A toggle you set in the session beats the config.
2. A block that tests a higher-ranked fact beats a lower one. From lowest to highest the ranks are
   `defaults`, model, agent or kind or tools, flag, session.
3. A statement that names a rule beats one that reaches it through a set.
4. An `exclude` beats an `include`.

`explain` shows which line decided a rule in a given context, quoting it as the config writes it:
`config.yaml:40`, the condition, and a reference such as `exclude bash.shell-scripts`.
