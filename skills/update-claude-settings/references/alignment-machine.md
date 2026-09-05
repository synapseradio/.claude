# The Reconcile machine

`Sweep` in SKILL.md runs `Reconcile` once per variant. This document is
`Reconcile`. Read it in full before running a sweep.

## Contents

- [States](#states)
- [Acquire](#acquire)
- [AuditBase](#auditbase)
- [Survey](#survey)
- [Project](#project)
- [Consult](#consult)
- [Seal](#seal)
- [Apply](#apply)
- [Verify](#verify)
- [Resurvey](#resurvey)
- [Idempotence](#idempotence)
- [The lift gate](#the-lift-gate)

Every command below takes `VARIANT` as the absolute path of the file under
reconciliation, and reads the predicates from
[`predicates.jq`](predicates.jq).

## States

| State | Entry condition | Exits |
|-------|-----------------|-------|
| `Acquire` | The sweep reached this variant | `HaltBaseInvalid`, `HaltVariantInvalid`, `AuditBase` |
| `AuditBase` | Both files parsed | `HaltBaseInvalid`, `Survey` |
| `Survey` | Base is fit as a floor | `Consult`, `Project` |
| `Project` | No layer-one conflict remains open | `Project`, `Consult`, `Seal` |
| `Consult` | A fork is open | `Project`, `LiftAccepted`, `HaltDeclined` |
| `Seal` | Every action is settled | `Aligned`, `Apply` |
| `Apply` | The sealed bytes differ from disk | `Verify`, `HaltVariantInvalid` |
| `Verify` | The write succeeded | `Resurvey`, `Consult` |
| `Resurvey` | All three predicates hold | `Aligned`, `HaltReverted` |

Terminal states: `Aligned`, `HaltBaseInvalid`, `HaltVariantInvalid`,
`HaltDeclined`, `HaltReverted`. `Aligned` is the only success. There is no
terminal state for a file that is aligned except for some divergences,
because a human-accepted divergence writes a registry entry in the same plan
and thereby becomes an exemption, which leaves the file plainly aligned.

## Acquire

Record the variant's pre-image hash and parse both files. Nothing gets
written in this state.

```bash
shasum -a 256 VARIANT
jq -e . /Users/nick/.claude/settings.base.json > /dev/null && echo "base parses"
jq -e . VARIANT > /dev/null && echo "variant parses"
```

Base fails to parse: `HaltBaseInvalid`. The variant fails to parse:
`HaltVariantInvalid`. Both parse: go to `AuditBase`.

## AuditBase

Six preconditions on base alone. Any one failing gives `HaltBaseInvalid`,
which stops the whole sweep, since an unfit floor would propagate its own
defect into every variant.

Five of them run in one command:

```bash
jq -s --arg mode audit-base \
  -f /Users/nick/.claude/skills/update-claude-settings/references/predicates.jq \
  /Users/nick/.claude/settings.base.json VARIANT
```

| # | Precondition | Check name in that output |
|---|--------------|---------------------------|
| 1 | Base parses to a JSON object rather than an array or a scalar | `root-object` |
| 2 | `alignment` is present and well formed: an object, `exempt` an array of entries each carrying a non-empty `path` and `why`, every path segment matching `[A-Za-z0-9_*-]+`, `notAVariant` an array of non-empty strings, `keyed` an object whose values name identity functions this skill defines | `registry-well-formed` |
| 3 | Base names nothing exempt: no leaf path matches a registry pattern, no leaf key ends in a secret-shaped word, no leaf value carries a credential shape | `base-holds-nothing-exempt` |
| 4 | `permissions.allow`, `permissions.deny`, and `permissions.ask` are pairwise disjoint within base | `permissions-disjoint-within-base` |
| 5 | Base is unambiguous about its own identities: no scalar array holds two members sharing a normalization, and no keyed-object array holds two members sharing a key or a member with no key | `base-unambiguous` |

The output object carries `"ok": true` when all five hold. jq exits 2 when a
named file is missing and still prints a result computed from what it read,
so read jq's exit status alongside `"ok"`.

The sixth runs separately, since jq cannot test the filesystem:

```bash
jq -r --arg home "$HOME" '
  (.hooks // {}) | .[][] | .hooks[]? | select(.type == "command") | .command
  | [splits("\\s+")] | map(select(test("/"))) | (.[0] // empty)
  | sub("^\\$HOME"; $home) | sub("^~/"; $home + "/")
' /Users/nick/.claude/settings.base.json \
| while IFS= read -r p; do [ -e "$p" ] || echo "MISSING $p"; done
```

Precondition 6 holds when that command prints nothing. It takes the first
whitespace-separated token containing a slash as the script path, which is
where a command hook's script sits after the interpreter word. A hook whose
script is gone would propagate into every variant and fail on every tool
call.

## Survey

Walk base and the variant together from the root and classify every path.
Base's `alignment` key is the registry rather than a setting, so delete it
from base before the walk. It never propagates into a variant.

**Path notation.** Join keys with `.` and elide array indices, so
`hooks.PreToolUse.hooks` names the inner array of every group under that
event. Registry patterns and `keyed` patterns match against this notation.

### The exemption pre-filter

Test the path before reading the classification table. A hit gives the
verdict `Exempt`, which produces no action, makes the path no lift candidate,
and stops the walk there. A path is exempt when any of these holds:

- A pattern in `alignment.exempt` matches it. A pattern matches a path when
  the two hold the same number of segments and each pattern segment matches
  its path segment, with `*` matching any run of characters inside one
  segment and nothing across a `.`.
- Its last segment ends in `TOKEN`, `KEY`, `SECRET`, `PASSWORD`, or
  `CREDENTIAL`, compared without regard to case.
- Its value is a string carrying a credential shape: a known credential
  prefix such as `sk-`, `ghp_`, `github_pat_`, `xoxb-`, `AKIA`, `AIza`,
  `glpat-`, `npm_`, `hf_`, or `Bearer `, or the form of a long opaque token,
  twenty or more characters from `[A-Za-z0-9_-]` followed by `.` and eight
  or more of the same.

The last two clauses are the guard, and a registry cannot replace it because
a registry covers only a secret somebody already registered. The guard only
ever adds exemptions, so it cannot open a hole.

The pre-filter runs first so an identity-linking key never reaches a later
test and never becomes a lift candidate.

### Type states and the classification table

Each side of a path sits in one of five states: `Absent`, `Null`, `Scalar`
(string, number, or boolean), `Array`, `Object`.

Rows are base's state, columns the variant's.

| base \ variant | Absent | Null | Scalar | Array | Object |
|---|---|---|---|---|---|
| **Absent** | unreachable | VariantOnly | VariantOnly | VariantOnly | Recurse |
| **Null** | Add | Satisfied | Conflict(scalar) | Conflict(type) | Conflict(type) |
| **Scalar** | Add | Conflict(scalar) | [scalar rule](#the-scalar-rule) | Conflict(type) | Conflict(type) |
| **Array** | Add | Conflict(type) | Conflict(type) | [array rule](#the-array-rule) | Conflict(type) |
| **Object** | Add | Conflict(type) | Conflict(type) | Conflict(type) | Recurse |

Twenty-four cells carry a verdict. Absent against Absent is unreachable
because the walk visits only paths one of the two files names, so its
emptiness is an argument rather than an omission.

| Verdict | Action |
|---------|--------|
| `Satisfied` | None |
| `Exempt` | None, and the path is no lift candidate |
| `Recurse` | None at this path; walk into the union of the two objects' keys |
| `Add` | Write base's value at this path in the variant, whole |
| `Corrected` | Replace the variant's value with base's spelling |
| `VariantOnly` | None in align mode; a lift candidate in lift mode |
| `Conflict(kind)` | An open fork, go to `Consult` |

Base Absent against variant Object recurses rather than stopping, so that
each leaf under it becomes its own path. That is what keeps `env` from being
treated as one unit: `settings.json` and the GLM profile share five `env`
keys, and only the identity-linking siblings are exempt.

### The scalar rule

1. The two values are equal: `Satisfied`.
2. Both are strings and equal after normalization: `Corrected` toward base's
   spelling.
3. Otherwise: `Conflict(scalar)`.

### Normalization

Applied to a string, in this order:

1. Trim leading and trailing whitespace.
2. Strip a leading interpreter word and the whitespace after it: `bash`,
   `sh`, `zsh`, `node`, `python3`, `python3.N`, or `uv run`.
3. Rewrite a leading `~/` to `/`.
4. Collapse every run of `/` to a single `/`.

The `norm` function at the top of [`predicates.jq`](predicates.jq) is the
definition. Read it before implementing the merge by hand.

Normalization is what makes `//tmp` a corrupted spelling of `/tmp` rather
than a legitimate variant-only addition, and what maps a bare
`verify-marks.py` command onto base's `python3.14`-prefixed form, so the
variant gains the interpreter through `Corrected` instead of through a human
answering a question. It pairs nothing across the permission lists, which is
correct: `WebFetch` is a corruption of nothing and reaches
[`Project`](#project) as `VariantOnly`.

### The array rule

Three kinds, chosen by the array's elided path.

**Scalar-set**, when every member of both arrays is a scalar:

- A base member with no normalization-equal variant member: `Add`.
- A base member whose variant counterpart is equal after normalization but
  not literally: `Corrected`, which replaces the variant's member with
  base's spelling. The variant's member goes away, which is what the residue
  predicate later proves.
- A variant member matching no base member: `VariantOnly`.
- Output order: base's members in base's order and base's spelling, then the
  residual variant-only members in their existing relative order.

**Keyed-object**, when the path matches a pattern in `alignment.keyed`:

1. Key every base member and every variant member with the path's identity
   function. A variant member yielding no key makes the whole array
   `Conflict(unkeyed)`.
2. Collapse variant members sharing a key into one, folding left to right.
   Folding two members applies this same table with the earlier member on
   base's side, so the earlier spelling wins wherever the two normalize
   equal. A `Conflict` inside a fold is a `Conflict` for the array.
3. For each base key present in the collapsed variant, recurse into the pair
   of members as Object against Object.
4. For each base key the variant lacks, `Add` the base member whole.
5. Variant keys base does not name are `VariantOnly`.
6. Output order: base's keys in base's order, then residual variant-only
   keys in their existing relative order.

Step 2 collapses two `hooks.PreToolUse` groups both keyed `Bash` into one
group. A plain array union would yield three groups and register two of the
scripts twice each, so the pass would double hook execution.

**Everything else**, including an array mixing scalars with objects:
`Conflict(unkeyed)`. This keeps the table total when the CLI grows a key
nobody anticipated. Resolving it registers an identity function in
`alignment.keyed`, which is a change to the floor and gets reviewed in git.

### Identity functions

`alignment.keyed` maps a path pattern to one of these names.

| Name | Key |
|------|-----|
| `matcher` | The member's `matcher` field, taken literally, with an absent field keying as null. Matchers are regexes, so normalization does not apply to them. |
| `hookPayload` | The pair of the member's `type` and the normalization of the first present of `command`, `prompt`, `agent`. A member naming none of the three has no key. |

`hookPayload` carries `type` alongside the payload, since a prompt hook and
an agent hook holding identical text are different behaviors.

Check uniqueness under these functions with the `keys` mode:

```bash
jq -s --arg mode keys \
  -f /Users/nick/.claude/skills/update-claude-settings/references/predicates.jq \
  /Users/nick/.claude/settings.base.json VARIANT
```

### Exits

Any `Conflict` sends the file to `Consult`. Otherwise go to `Project`.

## Project

Apply every layer-one action to an in-memory copy of the variant, then
evaluate the coupled invariants against that copy. A per-path floor rule is
necessary and not sufficient, because a contradiction can be a property of
the projected result while every input file is clean. Base, `settings.json`,
and the GLM profile hold pairwise disjoint permission lists as they sit, so
the contradiction the next paragraph repairs is invisible before projection.

**PermissionsDisjoint.** Within the projected variant, `permissions.allow`,
`permissions.deny`, and `permissions.ask` are pairwise disjoint. For an entry
appearing in two projected lists:

- Base names it in exactly one of the three: keep it there, remove it from
  the other, append that removal as an action, and re-enter `Project`.
- Base names it in none: `Conflict(coupled)`, since no direction is settled.
  Go to `Consult`.
- Base naming it in two cannot happen, because AuditBase precondition 4
  rejects such a base.

This carries base's `WebFetch` and `WebSearch` deny entries into a variant
that allows them, and it does so as one invariant rather than as a rule about
those two names. Web access routes through the tavily and linkup MCP tools
and `Bash(tvly:*)`, which base already allows.

No violation remains: go to `Seal`.

## Consult

Ask one AskUserQuestion per open fork, and ask every open fork in one call.
State in each option what gets written if the user picks it.

| Fork | Question | Options |
|------|----------|---------|
| `Conflict(scalar)` | Base and the variant hold different values at PATH | Take base's value. Register PATH exempt, which also removes PATH from base, since precondition 3 requires base to name nothing exempt. Lift the variant's value into base, offered in lift mode alone. Halt. |
| `Conflict(type)` | Base holds one type at PATH and the variant another | Replace the variant's value with base's, whole. Register PATH exempt and remove it from base. Halt. |
| `Conflict(unkeyed)` | PATH is an array of objects with no identity function | Register an identity function for PATH in `alignment.keyed`. Replace the variant's array with base's, whole. Register PATH exempt and remove it from base. Halt. |
| `Conflict(coupled)` | ENTRY appears in two projected permission lists and base names it in none | Keep it in allow. Keep it in deny. Keep it in ask. Halt. |
| `Q-Lift` | The variant names PATH and base does not | Lift it into base. Leave it in the variant alone. Register PATH exempt. |
| `Q-Verify-Failed` | The written file fails predicate P with these violations | Restore the backup and halt. Re-run Reconcile from Acquire on the restored file. |

Resolving a fork by keeping the variant's value always writes a registry
entry in the same plan. That is what stops the same question from firing on
every future pass.

Registering a path base names removes that path from base in the same plan,
since precondition 3 requires base to name nothing exempt. Say so in the
option text, because it drops a value from the floor for every profile.

**Exits.** A resolved fork or a registry entry sends the file back to
`Project`. Accepting a lift gives `LiftAccepted`, which is unavailable in
align mode. Choosing to halt, or no answer arriving, gives `HaltDeclined`.

## Seal

Serialize the projected variant and diff it against disk.

Serialization is byte-stable: base's key order first for keys base names,
then the variant's residual keys in their existing relative order; the same
rule for array members; two-space indentation; a trailing newline. No step
sorts or deduplicates by a rule a later pass would apply differently. Those
bytes are what `jq .` produces for the merged document, so after writing,
`diff <(jq . VARIANT) VARIANT` prints nothing.

The diff is empty: `Aligned`. Otherwise go to `Apply`.

## Apply

Back the variant up, then write the sealed bytes and move them into place.

```bash
BR=$(git -C /Users/nick/.claude branch --show-current)
DIR=/Users/nick/.claude/scratchpad/$BR/update-claude-settings
mkdir -p "$DIR"
cp VARIANT "$DIR/$(basename VARIANT).pre-$(date -u +%Y%m%d-%H%M%S).json"
```

Write the sealed JSON with the Write tool to `VARIANT.tmp` beside the
variant, then run `mv VARIANT.tmp VARIANT`. The move within one directory is
atomic, so no reader ever sees a half-written settings file.

The write or the move failing gives `HaltVariantInvalid`. Otherwise go to
`Verify`.

## Verify

Three predicates against the file read back from disk. Each one is
independent of the merge logic, so a bug in the merge cannot pass its own
check.

```bash
P=/Users/nick/.claude/skills/update-claude-settings/references/predicates.jq
B=/Users/nick/.claude/settings.base.json
for M in floor disjoint residue; do
  jq -s --arg mode "$M" -f "$P" "$B" VARIANT
done
```

| Predicate | Claim | What it catches that the others miss |
|-----------|-------|--------------------------------------|
| `floor` | Every leaf pair base names, with array indices elided, appears in the variant | A key or member that never got copied down |
| `disjoint` | The variant's permission lists stay pairwise disjoint | A contradiction, which the floor predicate cannot see because the floor checks presence and never absence |
| `residue` | No scalar array holds two members sharing a normalization | A corrupted spelling left standing beside the correct one, which is how a `Corrected` removal proves it happened |

All three hold: go to `Resurvey`. Any failing: go to `Consult` with
`Q-Verify-Failed`.

Then run `claude doctor` once as a smoke test. It is weak: it catches a file
the CLI cannot load and nothing subtler. Treat a clean run as no evidence
about alignment.

## Resurvey

Run the `keys` mode against the written file as the cheapest first test, then
run [Survey](#survey)'s body against it and require an empty action list.

An empty list gives `Aligned`. A non-empty list means the merge produced
something the next pass would change, so restore the backup taken in
[Apply](#apply) and end at `HaltReverted`.

Resurvey executes the second run's classification inside the first, so the
idempotence check cannot drift from the merge.

## Idempotence

Every action is a function of base and the variant, never of the run, and
every action lands its path in a category that produces no action on the next
pass. A human-resolved conflict included, because keeping the variant's value
writes a registry entry in the same plan.

## The lift gate

A path moves from a variant into base only through a lift, and only when
every one of these holds.

| # | Clause | How to check it |
|---|--------|-----------------|
| 1 | Base does not already carry the candidate | `base-does-not-carry-it` in the `lift-gate` mode |
| 2 | No registry pattern matches the path | `no-registry-match` |
| 3 | The secret guard stays silent on the path and the value | `secret-guard-silent` |
| 4 | The value carries no hostname, no port, no absolute path outside `$HOME`, and no credential shape | `value-carries-no-locator` |
| 5 | Projected base still satisfies every AuditBase precondition | Write the projected base to a scratchpad file and run the `audit-base` mode against it |
| 6 | A human chose it | AskUserQuestion, fork `Q-Lift` |

Clauses 1 through 4 run in one command:

```bash
jq -s --arg mode lift-gate --arg kind path --arg path DOTTED.PATH --argjson value JSON \
  -f /Users/nick/.claude/skills/update-claude-settings/references/predicates.jq \
  /Users/nick/.claude/settings.base.json VARIANT
```

Pass `--arg kind member` instead for one candidate member of a scalar-set
array base already names, such as `permissions.allow`. Under `kind path`,
clause 1 requires base to name nothing at or above the path. Under
`kind member`, it requires base's array at that path to hold no member equal
to the candidate after normalization.

An accepted lift writes base and restarts the sweep.
