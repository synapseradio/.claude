---
name: update-claude-settings
description: Configure the Claude Code harness through its settings files, and reconcile every settings variant against settings.base.json. Requests for automatic behavior, phrased 'from now on when X', 'each time X', 'whenever X', 'before X' or 'after X', need a hook in a settings file, since the harness runs hooks and no memory entry or preference can. Use this for permissions such as 'allow npm commands' or 'move that permission to user settings', for env vars such as 'set DEBUG=true', for writing or troubleshooting hooks, for MCP server keys, plugin keys, sandbox rules, and for any edit to settings.json, settings.base.json, settings.local.json or a settings.PROFILE.json variant. Use it for alignment work too, such as 'align my settings', 'sync settings.json with base', 'my settings drifted', 'the GLM profile is missing its hooks', or 'reduce permission prompts'. Suggest /config only for keys settings.base.json does not name, such as theme, editorMode or verbose.
---

# Update Claude settings

Two kinds of work run from here. Pick one before doing anything else.

- The user wants a setting changed, a hook written, a permission added, or a
  hook debugged. Go to [Editing one setting](#editing-one-setting).
- The user wants the settings files reconciled with each other, or reports
  drift, or asks to reduce permission prompts. Go to
  [The alignment sweep](#the-alignment-sweep).

## The files

| Path | Role | Git | Loaded by the CLI |
|------|------|-----|-------------------|
| `/Users/nick/.claude/settings.base.json` | The policy floor | Tracked | No |
| `/Users/nick/.claude/settings.json` | User scope, what the CLI reads | Ignored | Yes |
| `/Users/nick/.claude/settings.PROFILE.json` | A provider or profile variant | Ignored | On demand |
| `PROJECT/.claude/settings.json` | Project scope, team-wide | Committed | Yes |
| `PROJECT/.claude/settings.local.json` | Project scope, personal overrides | Gitignored | Yes |

Settings load user, then project, then local, and a later file overrides an
earlier one.

`settings.base.json` states policy. No CLI reads it, so a key in it changes
nothing by itself. It reaches the running configuration through the
alignment sweep, which copies it down into every variant.

The variants of user scope are the files matching
`/Users/nick/.claude/settings.*.json`, minus `settings.base.json`, minus every
basename listed in `alignment.notAVariant`, plus
`/Users/nick/.claude/settings.json`. Name variants through that glob and never
through a list you wrote down, since a profile gets added or renamed without
notice.

## Before any edit

**Read the target file first.** Every time, including files you wrote earlier
in the same session.

**Merge, never replace.** Writing an array or an object wholesale drops
everything already in it. This is wrong:

```json
{ "permissions": { "allow": ["Bash(npm *)"] } }
```

This is right, since it keeps what was there:

```json
{
  "permissions": {
    "allow": ["Bash(git *)", "Edit(.claude)", "Bash(npm *)"]
  }
}
```

**Ask when the request is ambiguous.** Put the question through
AskUserQuestion, one question per fork, before writing anything. Ask when the
target file is unclear, when adding to an array and replacing it both read as
plausible, and when several values fit.

**Validate after writing.** Run `jq -e . FILE`. A malformed settings file
silently disables every setting in it.

## Editing one setting

### Which file the change lands in

| The change | Where it goes |
|------------|---------------|
| Anything the user wants to hold across every profile: hooks, permissions, sandbox rules, policy defaults | `settings.base.json`, then run [the alignment sweep](#the-alignment-sweep) to push it down |
| Something true of one profile alone: its endpoint, its credentials, its model pins | That profile's variant, and register the path in `alignment.exempt` |
| Something scoped to one project | That project's `.claude/settings.json`, or `.claude/settings.local.json` for a personal override |

A hook is policy. Hooks belong in `settings.base.json`, and the sweep carries
them into every variant. Writing a hook into `settings.json` alone leaves
every other profile without it.

### Choosing between /config and a direct edit

Suggest `/config` only for a key that `settings.base.json` does not name.
Check before suggesting it:

```bash
jq -r 'del(.alignment) | keys[]' /Users/nick/.claude/settings.base.json
```

`/config` writes `settings.json` and bypasses the floor, so for a key base
names it produces exactly the drift the sweep exists to remove. As base
stands, these nine keys are off limits to `/config`: `autoUpdatesChannel`,
`cleanupPeriodDays`, `includeCoAuthoredBy`, `alwaysThinkingEnabled`,
`autoMemoryEnabled`, `autoCompactWindow`, `tui`, `includeGitInstructions`,
`showClearContextOnPlanAccept`. Re-read the list from the command above
rather than trusting that enumeration.

`/config` suits `theme`, `editorMode`, `verbose`, `model`, `language`, and
`permissions.defaultMode` while base leaves them unnamed.

Edit a file directly for hooks, permission rules, environment variables, MCP
server configuration, plugin configuration, and sandbox rules.

### The steps

1. Clarify anything ambiguous through AskUserQuestion.
2. Decide the target file from the table above.
3. Read the target file.
4. Merge the change into what is there.
5. Write with the Edit tool, or the Write tool for a new file.
6. Validate with `jq -e . FILE`.
7. Where the change landed in `settings.base.json`, run the alignment sweep
   so the running configuration picks it up.
8. Tell the user what changed and in which file.

For what a valid change looks like, read
[`references/settings-reference.md`](references/settings-reference.md). For
anything touching hooks, read
[`references/hooks-reference.md`](references/hooks-reference.md), which
carries the events table, the three hook types, the stdin and stdout
contracts, and a seven-step flow for constructing a hook and proving it
fires.

## The alignment sweep

### What alignment means

A variant is aligned with base when its arrays contain every entry base
lists, its objects contain every key base names recursively, and its scalars
match base's exactly wherever base names them. A variant stays free to hold
keys base never mentions.

Content flows base into a variant on every ordinary pass. Content flows a
variant into base only in lift mode, which a human starts.

### Two modes, fixed for a whole sweep

**Align mode** propagates base into every variant. The only key it writes in
base is `alignment`, and only when a human answers a question by choosing to
register an exemption. No setting value moves from a variant into base in
align mode.

**Lift mode** additionally offers paths a variant names and base does not as
candidates for base, one human answer each, and every candidate passes the
six-clause gate in
[`references/alignment-machine.md`](references/alignment-machine.md#the-lift-gate).
Run lift mode only when the user asks for it. Both variants hold top-level
keys base leaves unnamed, `model` and `theme` among them, so an automatic
consensus lift would propose pinning a model into the policy floor on every
routine run.

### Sweep

1. Enumerate the variants in fixed lexical order:

   ```bash
   ls /Users/nick/.claude/settings.json /Users/nick/.claude/settings.*.json 2>/dev/null | sort -u | \
   jq -R -s -r --slurpfile base /Users/nick/.claude/settings.base.json '
     ($base[0].alignment.notAVariant // []) as $skip
     | split("\n") | map(select(length > 0))
     | map(select((split("/") | last) as $n
         | $n != "settings.base.json" and ($skip | index($n) | not)))
     | sort | .[]'
   ```

2. Confirm each enumerated variant is readable. Two mechanisms can refuse a
   read: the `Read(...)` entries in `permissions.deny`, and the PreToolUse
   hooks that base registers, which cover the Read tool and Bash alike. A
   variant whose name matches a secret-shaped pattern is the case to expect.
   Where a read comes back denied, leave that variant out of this sweep,
   report it to the user with the exact command that got denied, and name the
   two ways forward: the user runs the reads in the session with
   `! COMMAND`, or the user amends whichever rule refused it. Do not
   restructure a command to slip past the guard.

3. Run [Reconcile](#reconcile) on each readable variant in that order.

4. Where a Reconcile ends in `LiftAccepted`, write the accepted lift into
   base and restart the sweep from step 1. Restarting terminates, because
   each lift strictly enlarges the set of paths base names, drawn from a
   candidate pool that does not grow during a sweep.

5. The sweep ends when every Reconcile ended in `Aligned`, or at the first
   Halt.

### Reconcile

Read [`references/alignment-machine.md`](references/alignment-machine.md) in
full before running step 3, and work from it. It carries `Reconcile`'s nine
states, the six AuditBase preconditions with their commands, the
classification table, the normalization and array rules, the coupled
invariant evaluated on the projected result, the questions `Consult` asks,
the three verification predicates, and the lift gate.

Reconcile ends in one of five terminal states. `Aligned` is the only success.

| Terminal state | Meaning |
|----------------|---------|
| `Aligned` | The variant satisfies the floor, and a second pass would change nothing |
| `HaltBaseInvalid` | Base is unfit to serve as a floor, so the whole sweep stops |
| `HaltVariantInvalid` | The variant failed to parse, or the write failed |
| `HaltDeclined` | A human chose to halt, or no answer arrived |
| `HaltReverted` | The written file would still change on a second pass, so the backup got restored |

Report the terminal state of every variant when the sweep ends, along with
what changed in each file.

## The registry

`settings.base.json` carries the registry under a top-level `alignment` key.
Base is never loaded by the CLI, so a non-standard key costs nothing at
runtime; base is the only tracked settings file, so the registry inherits git
history and review; and an exemption is a statement about the floor, so it
belongs in the commit that changes the floor. The published schema sets
`additionalProperties: true`, so the key passes schema validation.

```json
{
  "alignment": {
    "exempt": [
      { "path": "env.ANTHROPIC_AUTH_TOKEN", "why": "A live credential belonging to one account." }
    ],
    "notAVariant": ["settings.local.json"],
    "keyed": {
      "hooks.*": "matcher",
      "hooks.*.hooks": "hookPayload"
    }
  }
}
```

| Key | Contract |
|-----|----------|
| `exempt` | An array of objects, each carrying `path`, a segment-level path pattern, and `why`, prose a reviewer reads. Every segment matches `[A-Za-z0-9_*-]+`, and `*` matches inside one segment alone. |
| `notAVariant` | An array of basenames the variant glob matches and the sweep skips. |
| `keyed` | An object mapping a path pattern to an identity function name, one of `matcher` or `hookPayload`. |

An `exempt` entry has one effect and no sub-cases: it blocks propagation from
base into a variant and blocks lifting from a variant into base, both at
once.

Entries are segment-level patterns rather than subtree exemptions, and the
measurement demands it. `env` is not specific to one profile:
`settings.json` carries `CLAUDE_CODE_ENABLE_TASKS`,
`CLAUDE_CODE_ENABLE_TELEMETRY`, `DISABLE_EXTRA_USAGE_COMMAND`,
`ENABLE_PROMPT_CACHING_1H`, and `ENABLE_TOOL_SEARCH`, and the GLM profile
carries those same five with identical values. Exempting `env` wholesale
would sweep five legitimate consensus keys out of view.

`notAVariant` lists `settings.local.json` because the glob
`settings.*.json` would match a user-scope file of that name, which is a
partial overlay rather than a full configuration. Floor-aligning it would
inflate every local override with the whole of base.

## Reducing permission prompts

The built-in `fewer-permission-prompts` skill scans transcripts for
repeated read-only tool calls and proposes an allowlist. Its own behavior
writes that allowlist to a project `.claude/settings.json`, which bypasses
base entirely.

1. Invoke `Skill(fewer-permission-prompts)` for the scan.
2. Take its proposal list as data and discard its write target. Write no
   project settings file from it.
3. Inject each proposed rule as a synthetic lift candidate on
   `permissions.allow` and run the full lift gate on each, from
   [`references/alignment-machine.md`](references/alignment-machine.md#the-lift-gate):

   ```bash
   jq -s --arg mode lift-gate --arg kind member --arg path permissions.allow \
     --argjson value '"Bash(gh pr list:*)"' \
     -f /Users/nick/.claude/skills/update-claude-settings/references/predicates.jq \
     /Users/nick/.claude/settings.base.json /Users/nick/.claude/settings.json
   ```

4. Present the candidates that pass clauses 1 through 5 through
   AskUserQuestion as fork `Q-Lift`. Report each blocked candidate with the
   clause that blocked it.
5. Write the accepted rules into `settings.base.json`, then run the sweep so
   they reach every variant.

No path exists by which a proposed permission enters a variant first, since
the only state that writes a variant is `Apply`, and `Apply` writes only what
`Seal` produced from base.

## Reference files

| File | Read it when |
|------|--------------|
| [`references/alignment-machine.md`](references/alignment-machine.md) | Running a sweep. Read it in full first, since it holds every state, precondition, rule, and predicate the sweep runs on |
| [`references/predicates.jq`](references/predicates.jq) | Running any check, or implementing the merge by hand and needing the exact `norm` definition |
| [`references/settings-reference.md`](references/settings-reference.md) | Writing any key: permissions, env, model, attribution, MCP, plugins, sandbox, and the rest |
| [`references/hooks-reference.md`](references/hooks-reference.md) | Writing, verifying, or debugging a hook |
| [`references/schema-cache.md`](references/schema-cache.md) | Confirming a key against the published schema, or refreshing the cached copy |
| `references/settings-schema.json` | Looking one property up with jq, never reading whole |
