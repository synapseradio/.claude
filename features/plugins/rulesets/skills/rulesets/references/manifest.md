# The manifest

Required reading: [The rulesets directory and manifest](../../../docs/manifest.md), the section
"The manifest" in full: its keys, the reference forms, the condition facts, and the precedence
orderings.

Every case here runs inside the frame SKILL.md sets: "Before any edit" first, "After any change"
last. After the edit, run `RUN CLI explain NAME --root ROOT` on each rule the edit names, once for
each kind of context the edit means to reach, naming that context with `--model`, `--agent`,
`--kind`, `--tools`, and `--flag`. A fact left out is absent, and flags left out are unset.

Write every list entry as a quoted string. An unquoted entry is an `unquoted-entry` error.

## 9. Declare a model or a flag

- A model: add `"NAME"` to `models`. A declared name claims each model identifier that continues it
  with `-` or `[`, and of two names claiming one identifier the longer wins. A `model` condition
  on an undeclared name skips its block, with a notice.
- A flag: add `"NAME"` to `flags`. A launch sets it through `RULESETS_FLAGS` (runtime reference,
  case 20), and a toggle sets it for later delegates (SKILL.md, Toggle). A launch flag the manifest
  leaves undeclared is dropped, with a notice.

Declaring alone changes no context, so the impact diff stays empty until a block tests the name.

## 10. A named ruleset

- Create: add `NAME: ["REF", ...]` under `rulesets`. `defaults`, `all`, `rules`, and `none` are
  reserved and draw `reserved-ruleset`.
- Spread: write `"NAME:*"` in any list, which stands for every entry of `NAME`.
- Edit: change its list; every list that spreads it changes with it, so read the impact diff
  across every context.
- Delete: remove each `"NAME:*"` reference first, then the ruleset. A ruleset that spreads itself,
  directly or through others, is a `ruleset-cycle` error.

## 11. A `when` block

Each item under `when` maps one quoted condition to one list:

```yaml
when:
  - "agent reviewer and not flag strict": ["voice@terse", "-brevity"]
```

A condition tests `model NAME`, `agent NAME`, `kind session` or `kind delegate`, `tools TOOL`,
`flag NAME`, and `session ID`, combined with `and`, `or`, `not`, and parentheses. `not` binds
tighter than `and`, and `and` tighter than `or`. A condition testing anything else is a
`condition-invalid` error, and its block applies nowhere.

- Add: append the item. Two items may share one condition.
- Edit: change the condition or the list in place, and read which contexts the impact diff names.
- Remove: delete the item, and confirm in the impact diff that only the contexts it reached
  changed.

## 12. Give a rule to a context, withhold it, or set its variant

Write a block whose condition holds in that context, or reuse one, and list:

| To | List |
| --- | --- |
| give the rule | `"NAME"` |
| withhold the rule | `"-NAME"` |
| set a variant | `"NAME@VARIANT"` |
| strike a variant, keeping the rule's inclusion | `"-NAME@VARIANT"` |

A block wins only over statements at a lower position, so a withhold in a `model` block loses to
an add in an `agent` block. Where the explain output shows the edit losing, go to case 14.

## 13. Change `defaults`

`defaults` applies in every context, at the lowest position. `"all:*"` gives every rule in the
pool at its default form. A remove in `defaults` loses to an add in any block.

## 14. A remove or a variant loses, or `check` reports a variant conflict

1. Run `RUN CLI explain NAME --root ROOT` with the facts of the context in question. Each
   attribute, inclusion and variant, opens on the winning line and lists the lines it beat, with
   file and line.
2. Read the winner's position. The orderings run, each settling only the ties the earlier ones
   leave: a toggle beats the manifest; a block testing a higher-ranked fact beats a lower one, the
   ranks running `defaults`, model, agent or kind or tools, flag, session; a statement naming the
   rule beats one reaching it through a ruleset; a remove beats an add.
3. Move the losing statement to a position above the winner:
   - test a higher-ranked fact in its condition, as `and kind delegate` lifts a `model` block to
     the agent rank;
   - or name the rule in the list where a ruleset spread reached it.
4. A `variant-conflict` error names two blocks that can both apply and set different variants at
   one position. Make their conditions exclusive with `not`, or lift one above the other.
5. Run `explain` again and confirm the intended line wins.
