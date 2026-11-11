# The config

Required reading: [The rulesets directory and config](../../../docs/config.md), the section
"The config" in full: its keys, list and block layout, the reference forms, the condition facts,
and the precedence orderings.

Every case here runs inside the frame SKILL.md sets: "Before any edit" first, "After any change"
last. After the edit, run `RUN CLI explain NAME --root ROOT` on each rule the edit names, once for
each kind of context the edit means to reach, naming that context with `--model`, `--agent`,
`--kind`, `--tools`, and `--flag`. A fact left out is absent, and flags left out are unset.

Write every list as words separated by whitespace, one or more per line, with no quotes, brackets,
or dashes. A flow list written in brackets is a `list-shape` error, and an `exclude` takes the place
of a leading `-`.

## 9. Declare a model or a flag

- A model: add `NAME` to `models`. A declared name claims each model identifier that continues it
  with `-` or `[`, and of two names claiming one identifier the longer wins. A `model` condition
  on an undeclared name skips its block, with a notice.
- A flag: add `NAME` to `flags`. A launch sets it through `RULESETS_FLAGS` (runtime reference,
  case 20), and a toggle sets it for later delegates (SKILL.md, Toggle). A launch flag the config
  leaves undeclared is dropped, with a notice.

```yaml
models: opus sonnet haiku
flags: strict
```

Declaring alone changes no context, so the impact diff stays empty until a block tests the name.

## 10. A named set

- Create: add `NAME: REF REF ...` under `sets`, or `NAME:` with `include` and `exclude` beneath it.
  A name holds no `.`, and `defaults`, `all`, `rules`, and `none` are reserved and draw
  `reserved-ruleset`.
- Spread: write `NAME.*` in any list, which stands for every entry of `NAME`. Write `NAME.RULE` to
  name one rule the set holds.
- Edit: change its list; every list that spreads it changes with it, so read the impact diff
  across every context.
- Delete: remove each `NAME.*` and `NAME.RULE` reference first, then the set. A set that spreads
  itself, directly or through others, is a `ruleset-cycle` error.

```yaml
sets:
  review: security-pass voice@terse
  lean:
    include: all.*
    exclude: voice
```

## 11. A block

A block is a top-level key that holds a condition, with its lists beneath:

```yaml
agent reviewer and not flag strict:
  include: voice@terse
  exclude: brevity
```

A condition tests `model NAME...`, `agent NAME...`, `kind session`, `kind delegate`, or `kind any`,
`tools TOOL...`, `flag NAME...`, and `session ID...`, combined with `and`, `or`, `not`, and
parentheses. Several values after one kind hold where any of them holds. `not` binds tighter than
`and`, and `and` tighter than `or`. A condition testing anything else is a `condition-invalid`
error, and its block applies nowhere.

A block holds `include`, `exclude`, `then`, and nested blocks. A nested block applies where its own
condition and every enclosing one hold:

```yaml
models: opus haiku
sets:
  planning: writing-plans
agent Plan:
  not model haiku:
    include: planning.*
```

- Add: write the key and its lists. A condition written twice as a key at one level is a
  `duplicate-key` error that skips both blocks; put a second list under the one key with `then`.
- Edit: change the condition or the lists in place, and read which contexts the impact diff names.
- Remove: delete the key with everything beneath it, and confirm in the impact diff that only the
  contexts it reached changed.
- Nest: move a block under another where it repeats the outer condition, then confirm the impact
  diff stays empty.

## 12. Give a rule to a context, withhold it, or set its variant

Write a block whose condition holds in that context, or reuse one, and list:

| To | Write |
| --- | --- |
| give the rule | `include: NAME` |
| withhold the rule | `exclude: NAME` |
| set a variant | `include: NAME@VARIANT` |
| strike a variant, keeping the rule's inclusion | `exclude: NAME@VARIANT` |

A rule held by a set may be written `SET.NAME`, which shows the set it belongs to where the rule is
used.

A block wins only over statements at a lower position, so an exclude in a `model` block loses to
an include in an `agent` block. Where the explain output shows the edit losing, go to case 14.

## 13. Change `defaults`

`defaults` applies in every context, at the lowest position. `all.*` gives every rule in the pool
at its default form. An exclude in `defaults` loses to an include in any block.

```yaml
defaults:
  include: all.*
  exclude: bash.shell-scripts
sets:
  bash: shell-scripts
```

## 14. A remove or a variant loses, or `check` reports a variant conflict

1. Run `RUN CLI explain NAME --root ROOT` with the facts of the context in question. Each
   attribute, inclusion and variant, opens on the winning line and lists the lines it beat, with
   file and line, each quoted as the config writes it, as `exclude bash.shell-scripts`.
2. Read the winner's position. The orderings run, each settling only the ties the earlier ones
   leave: a toggle beats the config; a block testing a higher-ranked fact beats a lower one, the
   ranks running `defaults`, model, agent or kind or tools, flag, session; a statement naming the
   rule beats one reaching it through a set; an exclude beats an include.
3. Move the losing statement to a position above the winner:
   - test a higher-ranked fact in its condition, as `and kind any` lifts a `model` block to the
     agent rank;
   - or name the rule in the list where a set spread reached it.
4. Where an exclude cancels a variant that an include in the same list sets, move the exclude
   under `then`, which forms a list of its own and leaves the variant standing.
5. A `variant-conflict` error names two blocks that can both apply and set different variants at
   one position. Make their conditions exclusive with `not`, or lift one above the other.
6. Run `explain` again and confirm the intended line wins.
