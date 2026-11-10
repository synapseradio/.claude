---
name: rulesets
description: Write, edit, inspect, and debug the rules a rulesets directory delivers to each session and delegate, and toggle what this session's next delegates receive. The directory holds a pool of rule files (rules/NAME.md, variants NAME@VARIANT.md) and a manifest.yaml of models, flags, named rulesets, defaults, and when blocks. Use it to add, edit, rename, split, or remove a rule or variant; give a rule to one model, agent, tool, or flag, or withhold it; clear check errors and warnings; explain why a context got or missed a rule; preview what an edit changes across contexts; gate a commit; turn a flag on or off for the delegates started next; launch with RULESETS_FLAGS; read what a session or delegate received; find why no rules arrive; set up a first rulesets directory, adopt an old rules folder, or eject to plain files. Use it whenever a request touches the rules pool, the manifest, a rule variant, a ruleset flag, or which rules a delegate gets, even where it never says "rulesets".
---

# Rulesets

A rulesets directory holds a pool of rule files and one manifest. The manifest decides which rules
each context receives, a context being the main session or one delegate. The plugin's hooks deliver
each context its rules and record what they delivered.

Arguments typed after the skill name: `$ARGUMENTS`

Where the arguments, or the request, name a toggle action, go to [Toggle](#toggle) and run it at
once. Otherwise find the case in [Routing](#routing), read the reference it names, and follow that
reference's workflow.

## Placeholders

The references write these placeholders. Expand each to its value here when you run a command.

| Placeholder | Value |
| --- | --- |
| `RUN` | `bash "${CLAUDE_PLUGIN_ROOT}/hooks/with-python.sh"` |
| `CLI` | `"${CLAUDE_PLUGIN_ROOT}/lib/rulesets/cli.py"` |
| `SCRIPTS` | `"${CLAUDE_SKILL_DIR}/scripts"` |
| `ROOT` | `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/rulesets"` |
| `STATE` | `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.tmp/rulesets-engine"` |
| `SESSION` | `${CLAUDE_SESSION_ID}`, this session's identifier |

`RUN CLI check --root ROOT` expands to
`bash "${CLAUDE_PLUGIN_ROOT}/hooks/with-python.sh" "${CLAUDE_PLUGIN_ROOT}/lib/rulesets/cli.py" check --root "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/rulesets"`.
The launcher finds an interpreter that runs the engine, Python 3.14 or later with PyYAML.

## Toggle

A toggle changes what the delegates this session starts afterwards receive. It leaves this
session's own rules, and every running delegate's, as they are.

| Action | Delegates started afterwards |
| --- | --- |
| `all` | receive every rule in the pool |
| `none` | receive no rule |
| `flag NAME` | hold the flag `NAME`, which the manifest declares |
| `unflag NAME` | do not hold the flag `NAME` |
| `clear` | compose from the manifest and the launch flags alone |

Read a plain request as its action: "turn on strict for my delegates" is `flag strict`, "stop giving
delegates strict" is `unflag strict`, "give my delegates no rules" is `none`. Run the command with
`ACTION` replaced by the action's words:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/with-python.sh" "${CLAUDE_PLUGIN_ROOT}/lib/rulesets/cli.py" toggle --session "${CLAUDE_SESSION_ID}" ACTION
```

Report the line it prints, in one sentence. Where it prints an error, the error is the whole report.
The later of `all` and `none` replaces the earlier, and a clear, a resume, or the session's close
ends every toggle.

## Routing

| # | Case | Reference |
| --- | --- | --- |
| 1 | Add a rule | [rules](references/rules.md) |
| 2 | Edit a rule's text, directly or through a render | [rules](references/rules.md) |
| 3 | Add a variant and set it in a block | [rules](references/rules.md) |
| 4 | Remove a rule or a variant | [rules](references/rules.md) |
| 5 | Rename a rule | [rules](references/rules.md) |
| 6 | Split a rule over 9,000 characters | [rules](references/rules.md) |
| 7 | Clear `check` warnings | [rules](references/rules.md) |
| 8 | Move a rule out of the harness's own rules folder into the pool | [rules](references/rules.md) |
| 9 | Declare a model or a flag | [manifest](references/manifest.md) |
| 10 | Create, edit, delete, or spread a named ruleset | [manifest](references/manifest.md) |
| 11 | Add, edit, or remove a `when` block | [manifest](references/manifest.md) |
| 12 | Give a rule to a context, withhold it, or set its variant for one context | [manifest](references/manifest.md) |
| 13 | Change `defaults` | [manifest](references/manifest.md) |
| 14 | A remove or a variant loses, or `check` reports a variant conflict | [manifest](references/manifest.md) |
| 15 | Show one context's full set of rules | [inspecting](references/inspecting.md) |
| 16 | Why a context got or missed a rule | [inspecting](references/inspecting.md) |
| 17 | What an edit changes across every context | [inspecting](references/inspecting.md) |
| 18 | The gate before a commit | [inspecting](references/inspecting.md) |
| 19 | Toggle all, none, flag, unflag, or clear | [Toggle](#toggle) |
| 20 | Launch with flags | [runtime](references/runtime.md) |
| 21 | What a session or a delegate actually received | [runtime](references/runtime.md) |
| 22 | No rules arriving | [runtime](references/runtime.md) |
| 23 | Prune a session's records | [runtime](references/runtime.md) |
| 24 | Try another wording of a rule and compare two sessions | [runtime](references/runtime.md) |
| 25 | First setup | [setup and migration](references/setup-and-migration.md) |
| 26 | Adopt an old corpus or rules folder | [setup and migration](references/setup-and-migration.md) |
| 27 | Eject to plain files | [setup and migration](references/setup-and-migration.md) |

## The files

| Path | Role | Written by |
| --- | --- | --- |
| `ROOT/manifest.yaml` | which rules each context receives | you, `scaffold.py`, `CLI adopt` |
| `ROOT/rules/` | the pool: `NAME.md` is a rule's default form, `NAME@VARIANT.md` a variant | you, `CLI split`, `scaffold.py`, `CLI adopt` |
| `ROOT/references/` | files a rule may cite | you |
| `ROOT/-render/` | composed renders for reading and editing, never read as rules | `CLI render`, `scaffold.py` |
| `STATE/` | delivery records and toggle state | the plugin's hooks, `CLI toggle` |

## Before any edit

1. Read `ROOT/manifest.yaml` and every file the edit touches, in full.
2. Take a snapshot into a new directory, and keep its path for the diff:
   `RUN SCRIPTS/impact.py snapshot --root ROOT --out "$(mktemp -d)/before"`.

## After any change

1. Take a second snapshot into another new directory, then run
   `RUN SCRIPTS/impact.py diff BEFORE AFTER`.
2. Run `RUN CLI render --root ROOT`.
3. Run `RUN SCRIPTS/gate.py --root ROOT`, and clear every error it reports before reporting.
4. Report the impact diff, and each file changed with what changed in it.
