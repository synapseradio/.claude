# Design: splitting harness configuration from one machine's secrets

This report records the design decision behind the `harness-config` plugin:
what problem it solves, which mechanism owns which decision, the approaches
considered including standing still, and the interfaces to build against.

## Contents

- [The problem](#the-problem)
- [Four mechanisms, one question](#four-mechanisms-one-question)
- [Who owns which decision](#who-owns-which-decision)
- [Approaches considered](#approaches-considered)
- [Comparison](#comparison)
- [The decision](#the-decision)
- [Interfaces](#interfaces)
- [Legal and illegal states](#legal-and-illegal-states)
- [Where types end and runtime checks begin](#where-types-end-and-runtime-checks-begin)
- [Integration points](#integration-points)

## The problem

Four mechanisms answer "which provider and which model does this harness run
on", none of them owns the answer, and every one of them reads or writes a
file that may hold a live credential, so the decision cannot be handed to a
second person without handing over this machine.

### How to falsify that statement

The claim fails if a second person, given only the tracked contents of this
repository, already reaches a working provider profile without editing a file
the repository does not name. Three checks say they do not:

| Check | Result |
|-------|--------|
| `git ls-files \| grep settings` | Names `settings.base.json` alone. Every provider variant is untracked, so nothing tracked carries an endpoint or a model pin. |
| `git ls-files \| grep cc-profile` | Empty. The switcher lives under `~/.dotfiles/shell/lib/private/`, outside this repository and unreadable by this session. |
| `grep -c source scripts/zai-api-key.sh` | One. The helper reads a file that exists on one machine, and the repository does not say which file or what it must contain. |

A second person therefore has the policy floor and none of the four
provider-identity mechanisms. The problem statement holds.

### What changes when it is solved

An observer checks six behaviours:

1. A second user with no secrets configured reaches a working profile using
   only commands this plugin ships.
2. `git check-ignore -v` names a rule for every settings variant name,
   including names no file uses yet.
3. A scan of the plugin directory for credential shapes, absolute `/Users`
   paths, and account identifiers reports nothing.
4. No test and no shipped script reads a settings file's values or an agent
   definition, and one command over the suite confirms it.
5. Every diagnostic reports key paths and never values.
6. No shipped script executes an `apiKeyHelper`.

## Four mechanisms, one question

The question decomposes into four decisions, and each mechanism answers some
of them without saying which are its own.

| Mechanism | What it decides today | What it also touches |
|-----------|-----------------------|----------------------|
| Settings variants (`settings.gemma.json`) | The endpoint and the eight model pins for one provider | The whole policy surface, since a variant is a complete settings file, and `env.ANTHROPIC_AUTH_TOKEN` sits in the exempt list, so a variant may legally hold a live token |
| The alignment machinery (`alignment` in `settings.base.json`) | Which paths are policy and which legitimately differ per profile | Nothing else, and this is the mechanism whose scope is already stated precisely |
| `cc-profile` under `~/.dotfiles/shell/lib/private/` | Which profile is active | Unknown; the path is denied to this session, so the design treats it as prior art and depends on none of it |
| `apiKeyHelper` (`scripts/zai-api-key.sh`) | Which credential the active profile authenticates with | The repository, because `.gitignore` allowlists `scripts/**`, so this helper is tracked today |

Two overlaps cause the trouble.

The first overlap: a variant file is both a profile definition and a settings
file. Nothing in the setup says which of its keys are provider identity and
which are policy, so the alignment sweep exists to answer that question after
the fact, one path at a time, against a registry. The registry is right and
the representation is what forces it to work so hard.

The second overlap: `env.ANTHROPIC_AUTH_TOKEN` and `apiKeyHelper` both answer
"which credential", and both sit in the exempt list. The design permits an
inline token and an indirected one equally, and prefers neither. An inline
token is the publishing hazard, and the only thing keeping it out of git is
the ignore layer.

## Who owns which decision

The plugin assigns each decision one owner and takes it away from everyone
else.

| Decision | Owner | How it reaches the running harness |
|----------|-------|------------------------------------|
| Policy true across every profile: hooks, permissions, sandbox rules, defaults | `settings.base.json` | The alignment sweep propagates it into every variant and into `settings.json` |
| Which paths a profile may own | `alignment.exempt` in `settings.base.json` | A profile declaring a path outside that set fails validation |
| Provider identity: the endpoint, the model pins, which credential source to use | One profile file under `${CLAUDE_PLUGIN_DATA}/profiles/` | Activation writes exactly the declared paths into `settings.json` |
| Which profile is active | One pointer file at `${CLAUDE_PLUGIN_DATA}/active` | Activation reads it; `current` reports it |
| The credential itself | A helper script outside the repository, named by path | Nothing in the plugin reads it or runs it; the harness runs it |

Read down that table and the four original mechanisms land as follows. The
alignment machinery keeps its job and loses nothing. Variant files stop being
the profile representation and become legacy files the plugin still keeps
aligned. `cc-profile`'s job moves into the plugin. `apiKeyHelper` keeps the
credential and gains a written contract.

One sentence states the split: **base owns policy, a profile owns provider
identity, a helper owns the secret by reference, and activation is a bounded
write.**

## Approaches considered

### C0: stand still

Keep the four mechanisms and publish nothing. The setup works today.

Assumption: nobody else needs this layer, and the account identifier already
sitting in the skill's forty hardcoded absolute paths, each naming one
account's config directory, costs nothing. This paragraph names the shape
rather than reproducing it, because `harness-guard.sh material` rejects the
literal form and rejected an earlier draft of this sentence.

Against the constraints: it violates no constraint on new work and fails
success criterion 1 outright. It also leaves finding 1 standing, which is a
private path with an account identifier in a tracked file.

### C1: de-personalise and ship the variants as the profiles

Move the skill into the plugin, replace every hardcoded path with a resolved
config directory, and add an activation command that copies
`settings.<name>.json` over `settings.json`. A profile stays a complete
settings file.

Core interaction: a profile is a full settings file; activation swaps files;
the alignment sweep keeps every variant at the floor.

Assumption: a complete settings file per profile is an acceptable
representation of provider identity.

Against the constraints: it satisfies the hard constraints and strains two of
them. Every variant remains a file where `env.ANTHROPIC_AUTH_TOKEN` is
exempt, so N profiles mean N files that may legally hold a token and N files
the ignore layer must catch. A file swap also overwrites whatever `/config`
wrote into `settings.json`.

### C2: derive the variants from base plus a profile

Profiles become small data files. A render step writes each
`settings.<name>.json` from base plus the profile, so drift stops being
possible for a variant.

Core interaction: profile data in, complete variant file out, activation
copies the derived variant to `settings.json`.

Assumption: a variant holds nothing worth keeping that base or the profile
does not name.

Against the constraints: that assumption is false against the real files.
Both variants carry top-level keys base leaves unnamed, `model` and `theme`
among them, as the skill's own text records. Generating would delete them. No
hard constraint falls, and a user would call the deletion a defect.

### C3: activation writes a declared path set

Profiles become small data files under `${CLAUDE_PLUGIN_DATA}/profiles/`.
Each profile declares exactly the paths it owns, bounded by
`alignment.exempt`. Activation writes those paths into `settings.json` and
touches nothing else. Variant files stay supported for whoever already has
them, and the alignment sweep keeps covering them.

Core interaction: `harness-profile.sh use NAME` reads the profile, checks
every declared path against base's exempt list and against a credential-name
guard, then applies the values to `settings.json` with one `jq` filter.

Assumption: `alignment.exempt` is the right bound on what a profile may own.
The exempt list is by definition the set of paths that legitimately differ per
profile, each carrying a written `why`, so the assumption is the registry's
own claim about itself.

Against the constraints: it satisfies every hard constraint. One file holds
one profile, and that file has no slot for a credential value.

### C4: activation prints environment exports

Activation writes no settings at all and prints `export` lines the user's
shell evaluates, since `ANTHROPIC_BASE_URL` and the model pins are already
environment variables.

Assumption: the harness honours these from the ambient environment, and the
credential can travel the same way.

Against the constraints: the environment has no `apiKeyHelper` equivalent, so
the credential would have to become an exported value, and activation would
print it. That contradicts the rule that no shipped script prints a secret.
Eliminated on a hard constraint.

### C5: two plugins

Split the policy floor and its alignment into one plugin and provider
profiles into another, since the two decisions are separable.

Assumption: somebody wants one without the other.

Against the constraints: the marketplace takes exactly one entry for this
capability, so this is out of bounds. Eliminated on a hard constraint.

## Comparison

| | C0 stand still | C1 variants as profiles | C2 derive variants | C3 declared path set | C4 env exports | C5 two plugins |
|---|---|---|---|---|---|---|
| Files that may legally hold a credential | 2 or more | one per profile | one per profile | zero | zero, but the value is exported | one per profile |
| Drift surface | every variant, hand-edited | every variant, hand-edited | none for derived variants | the declared paths only | none | every variant |
| Preserves keys base does not name | yes | no, a swap overwrites them | no, generation drops them | yes, the write is bounded | yes | no |
| Second user reaches a profile from nothing | no | yes | yes | yes | yes | yes |
| Reverting a switch | manual | swap back | re-render | rewrite the same paths | unset the exports | swap back |
| Existing alignment machinery reused | n/a | whole | partly, generation replaces the merge | whole | none | whole |
| Hard constraint violated | none, fails criterion 1 | none | none, deletes user state | none | H4, activation prints the token | H7, one entry only |

Two candidates fall on a hard constraint: C4 on the rule against printing a
secret, C5 on the single marketplace entry. C0 survives the constraints and
fails the first success criterion. C2 survives the constraints and destroys
user state. C1 and C3 both stand.

C1 and C3 differ on one dimension that decides it. C1 leaves one
credential-legal file per profile, and its only protection is the ignore
layer. C3 leaves zero, because a profile's credential field holds a path to a
helper rather than a token. Defense in depth wants the count at zero, since
that is the layer that still holds when every layer above it fails.

## The decision

**C3: activation writes a declared path set.** A profile that has no slot for
a credential cannot leak one, whatever the layers above it do.

### What each rejected candidate would need to become right

| Candidate | Reversal condition |
|-----------|--------------------|
| C0 stand still | The user decides this layer stays on one machine, at which point de-personalising the skill's paths is still worth doing on its own. |
| C1 variants as profiles | The harness gains a first-class profile switch that reads whole files, which makes a bounded write pointless. |
| C2 derive variants | `alignment.exempt` grows to cover everything a variant may hold, at which point a variant carries nothing worth preserving. |
| C4 env exports | The harness gains a helper-command environment variable, so provider identity travels in the environment with the credential still behind an indirection. |
| C5 two plugins | The marketplace convention changes to prefer narrow plugins over one entry per capability. |

### What this choice sacrifices

Four qualities go, deliberately. Nobody should restore them as an improvement.

**Hand-authority over the declared paths in `settings.json`.** Editing
`env.ANTHROPIC_BASE_URL` there by hand survives until the next activation,
which rewrites it from the active profile. The paths a profile declares belong
to the profile.

**A single representation.** Plugin profiles and legacy variant files coexist,
and the plugin diagnoses both. Deleting somebody's `settings.gemma.json` is
not the plugin's call, so the second representation stays.

**Taking effect immediately.** Activation writes `settings.json`, and the
running session keeps the configuration it started with. The switch lands on
the next session. No plugin can restart the CLI.

**The option of an inline token.** No profile can set
`env.ANTHROPIC_AUTH_TOKEN`, even though the registry exempts it. A user who
insists on one edits `settings.json` by hand, outside the plugin, and the
plugin's diagnostics report that the path is set without reporting its value.

## Interfaces

### Resolution of the three directories

Every script resolves three paths the same way, and each resolution takes an
override so a test never touches real user state.

| Name | Resolution | Why the override exists |
|------|------------|-------------------------|
| Config directory | `${CLAUDE_CONFIG_DIR:-${HOME}/.claude}` | `CLAUDE_CONFIG_DIR` is the documented override for the config root, so a test points it at a temporary directory and the scripts read fixtures there. |
| Plugin data directory | `${HARNESS_CONFIG_DATA:-${CLAUDE_PLUGIN_DATA:-<config>/plugins/data/harness-config}}` | `CLAUDE_PLUGIN_DATA` is set by the harness for a plugin hook. A skill's Bash call may not carry it, so the fallback derives the documented location, and `HARNESS_CONFIG_DATA` lets a test redirect it. |
| Plugin root | `${CLAUDE_PLUGIN_ROOT:-<the script's own parent's parent>}` | A script invoked by absolute path finds its own siblings without the harness setting anything. |

### The profile file

One file per profile at `<data>/profiles/<name>.json`.

```json
{
  "schemaVersion": 1,
  "name": "example",
  "describe": "One line the profile list shows.",
  "settings": {
    "apiKeyHelper": "~/.config/example-provider/api-key.sh",
    "env": {
      "ANTHROPIC_BASE_URL": "https://gateway.example.invalid/anthropic",
      "ANTHROPIC_DEFAULT_OPUS_MODEL": "example-large",
      "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "Example Large",
      "ANTHROPIC_DEFAULT_SONNET_MODEL": "example-medium",
      "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "Example Medium",
      "ANTHROPIC_DEFAULT_HAIKU_MODEL": "example-small",
      "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": "Example Small",
      "ANTHROPIC_DEFAULT_FABLE_MODEL": "example-fable",
      "ANTHROPIC_DEFAULT_FABLE_MODEL_NAME": "Example Fable"
    }
  }
}
```

| Field | Contract |
|-------|----------|
| `schemaVersion` | The integer `1`. A reader that meets a higher number stops rather than guessing. |
| `name` | Matches `^[a-z0-9][a-z0-9-]*$`, and is neither `base` nor `local`. The name reaches a filename and a settings-variant name, so it takes the narrower of the two alphabets. |
| `describe` | A non-empty single-line string. The profile list prints it, so it must carry nothing an account identifies. |
| `settings` | An object whose leaf paths are the paths this profile owns. Every leaf path passes both gates below. |

The declared path set passes two independent gates.

| Gate | Rule | What it alone catches |
|------|------|-----------------------|
| Exempt bound | Every leaf path in `settings`, with array indices elided, matches a pattern in `alignment.exempt` in `settings.base.json` | A profile reaching outside provider identity and overwriting policy, such as a profile that sets `permissions.allow` |
| Credential-name guard | No leaf path's last segment ends in `TOKEN`, `KEY`, `SECRET`, `PASSWORD`, or `CREDENTIAL`, compared without regard to case, and no leaf value carries a credential shape | A token written into a profile, which the exempt bound would permit, since `env.ANTHROPIC_AUTH_TOKEN` is exempt |

Neither gate subsumes the other. The exempt bound comes from a registry, so it
covers what somebody registered. The credential guard comes from a shape, so
it covers what nobody registered. `apiKeyHelper` passes the guard because its
last segment is `apiKeyHelper`, which ends in neither word, and because a
filesystem path carries no credential shape.

### The active pointer

`<data>/active` holds one line: the active profile's name, or nothing.

The pointer sits outside every settings file on purpose. A settings key naming
the active profile would be a path the profile itself owns, which is circular,
and it would put the answer inside a file the plugin must not read by value.

### The commands

| Command | Arguments | Effect | Exit |
|---------|-----------|--------|------|
| `harness-setup.sh` | none | Installs the ignore rules and the permission deny rules, creates the data directories, copies the helper template into place if absent, then runs every guard and prints the output | 0 when every guard passes |
| `harness-profile.sh list` | none | Prints each profile's name, its `describe`, and whether it is active | 0 |
| `harness-profile.sh show NAME` | a profile name | Prints the profile's key paths and its non-credential values; prints `apiKeyHelper` as a path and its file mode | 0, 3 when the profile is absent |
| `harness-profile.sh add NAME` | a profile name | Writes `<data>/profiles/NAME.json` from the template and prints the path to edit | 0, 4 when it already exists |
| `harness-profile.sh validate NAME` | a profile name, or `--all` | Runs both gates and the helper contract; prints one line per check | 0 when every check passes, 5 otherwise |
| `harness-profile.sh use NAME` | a profile name | Validates, backs up `settings.json`, writes the declared paths, updates the pointer | 0, 5 on a validation failure |
| `harness-profile.sh current` | none | Prints the active profile's name | 0, 6 when no profile is active |
| `harness-doctor.sh` | none | Reports why a profile is or is not in effect, by key path and never by value | 0 when the active profile is fully in effect, 7 otherwise |
| `harness-guard.sh ignore` | none | Runs `git check-ignore -v` against every variant name, real and hypothetical, and prints each result | 0 when every name is ignored, 8 otherwise |
| `harness-guard.sh material [DIR]` | a directory, default the plugin root | Scans for credential shapes, absolute `/Users` paths, and account identifiers | 0 when the scan is empty, 9 otherwise |
| `harness-guard.sh scripts` | none | Checks every script the plugin ships for a forbidden construct | 0 when clean, 10 otherwise |
| `harness-guard.sh all` | none | Runs the three guards above in order | 0 when all pass |
| `harness-align-check.sh` | none | Runs `audit-base` and the three verification predicates over every variant, value-free, and reports per variant | 0 when every variant is aligned, 11 otherwise |

Distinct exit statuses matter because a caller distinguishes "no profile
active" from "validation failed" without parsing prose.

### The `apiKeyHelper` contract

The helper is the only thing that ever holds the credential, and nothing in
the plugin reads it or runs it.

| Clause | Requirement | How the plugin checks it |
|--------|-------------|--------------------------|
| 1 | The path exists | `[[ -e "${path}" ]]` |
| 2 | The path is a regular file | `[[ -f "${path}" ]]` |
| 3 | The owner may execute it | `[[ -x "${path}" ]]` |
| 4 | Neither group nor other may read or write it, so the mode's last two digits are `00` | `stat` reports the mode; the check compares the string |
| 5 | The path resolves outside every git repository the plugin knows, and outside the plugin root | Compares the resolved path against the repository root and the plugin root as prefixes |
| 6 | It writes the credential to stdout and nothing else | Stated in the contract and never verified, because verifying it means running it |

Clause 6 is a contract the plugin states and declines to test. Running the
helper captures a token into a process, a variable, and potentially a
transcript. The plugin's validation therefore proves the helper is *installed*
and never that it *works*. A user learns it works when a session authenticates.

The template the plugin ships satisfies clauses 1 through 5 and deliberately
fails clause 6: it writes a placeholder to stdout and exits non-zero with a
message on stderr naming what to edit. It ships without the executable bit, so
copying it into place is a decision the user makes rather than a default.

## Legal and illegal states

The frame ruled certain states invalid. Each one below is unrepresentable or
rejected, and the mechanism that rejects it is named.

| State the frame rules out | What rejects it |
|---------------------------|-----------------|
| A profile carrying a credential value | The credential-name guard, on both the path and the value shape |
| A profile overwriting policy | The exempt bound |
| A profile named `base`, so `settings.base.json` becomes a variant | The name alphabet plus the two reserved names |
| A profile name with a slash or a dot, escaping the profiles directory | The name alphabet, `^[a-z0-9][a-z0-9-]*$` |
| An `apiKeyHelper` inside the repository, so it could be committed | Contract clause 5 |
| An `apiKeyHelper` readable by group or other | Contract clause 4 |
| Any code path that executes the helper | No script names the resolved helper path in a command position, and a guard greps every shipped script for the construct |
| A diagnostic printing a settings value | Every diagnostic reads through `jq -r 'paths(scalars) \| join(".")'` or an explicit non-credential subtree, and a guard greps for the alternatives |
| A test reading real user state | Scripts read the config directory only through `CLAUDE_CONFIG_DIR`, and a meta-test rejects any test file naming `$HOME` or a real settings path |
| An active pointer naming an absent profile | `harness-doctor.sh` reports it; `use` writes the pointer only after validation passes |

## Where types end and runtime checks begin

JSON carries no schema, so nothing here is checked before it runs. The
boundary sits at the entry of every command:

- `harness-profile.sh` validates the profile file's shape, its name, its
  declared path set, and the helper contract before any write. Past that
  point, the code treats the profile as well formed.
- `harness-align-check.sh` delegates to `predicates.jq`, which already returns
  an `ok` field per predicate, and reads jq's exit status alongside it, since
  jq exits 2 on a missing file while still printing a result.
- `harness-guard.sh` makes no assumptions and takes any directory.

Every command validates its own inputs rather than trusting a caller, because
each one is also a copy-pasteable command a user runs alone.

## Integration points

| Point | What connects | Contract |
|-------|---------------|----------|
| `settings.base.json`, key `alignment.exempt` | The exempt bound reads it | The plugin reads the registry and never writes it. Registering a new exempt path stays the skill's interactive job, because it changes the floor and belongs in a reviewed commit. |
| `settings.base.json`, key `permissions.deny` | `harness-setup.sh` merges the deny fragment | The merge adds entries and removes none. The plugin adds no hook entry, per the constraint. |
| `settings.json` | Activation writes the declared paths | The write is bounded to the paths the active profile declares. Every other key survives. |
| `.gitignore` at the repository root | `harness-setup.sh` installs the variant rules and `harness-guard.sh ignore` verifies them | Setup appends rules and never rewrites the allowlist. The verification runs `git check-ignore -v` per name, so an allowlist widened for another purpose shows up as a failure. |
| `skills/harness-profiles/` and `skills/update-claude-settings/` | The two skills call these scripts | A skill names a script by `${CLAUDE_PLUGIN_ROOT}` and never by an absolute path. |
| `references/predicates.jq` | `harness-align-check.sh` and the skill both invoke it | The modes and their output shape stay as they are, with one change recorded in the security model: `value-carries-no-locator` reports a classification rather than the offending string. |
