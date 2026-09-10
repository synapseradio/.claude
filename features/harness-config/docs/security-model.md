# Security model

This plugin ships mechanism and never material. The mechanism is how a
provider profile is defined, validated, activated, and diagnosed. The material
is the user's endpoints, credentials, private paths, and account identifiers,
which live outside this repository and stay outside it.

Four threats organise the layers. Each layer names what it catches, and what
catches its own failure.

## Contents

- [Threat 1: a credential reaches git](#threat-1-a-credential-reaches-git)
- [Threat 2: a credential reaches a model's context](#threat-2-a-credential-reaches-a-models-context)
- [Threat 3: a credential is captured by running the helper](#threat-3-a-credential-is-captured-by-running-the-helper)
- [Threat 4: a test or a script touches real user state](#threat-4-a-test-or-a-script-touches-real-user-state)
- [The rules, and the one command that checks each](#the-rules-and-the-one-command-that-checks-each)
- [What this model does not cover](#what-this-model-does-not-cover)

## Threat 1: a credential reaches git

### Layer 1.1: the ignore rules, outermost

`.gitignore` at the repository root ignores `*` and then allowlists specific
paths. Nothing enters git without a line naming it. That single fact is why
`settings.json` and `settings.gemma.json` are untracked today, and it is the
layer that holds without anybody thinking about it.

**Catches:** any settings variant, any profile file, any secrets file, staged
by accident or by a tool.

**Where it fails:** an allowlist entry widened for another purpose. This
plugin needs `features/**` allowlisted, and `features/**` is broad. A settings
variant placed under `features/harness-config/` would be tracked.

**What catches that failure:** layer 1.2.

`harness-setup.sh` installs the rules and `harness-guard.sh ignore` verifies
them, per name, with `git check-ignore -v`, including names no file uses yet.
Verification is separate from installation on purpose: installing proves a
line was written, and verifying proves git agrees.

### Layer 1.2: the material scan over tracked paths

`harness-guard.sh material [DIR]` scans a directory for three shapes:
credential prefixes and long opaque tokens, absolute paths under `/Users` or
`/home`, and account identifiers. It defaults to the plugin root, and a
reviewer points it at the repository root to widen the scope.

**Catches:** material inside a path the ignore layer allowlists, which is
exactly where the ignore layer is silent by design.

**Where it fails:** a shape the scan does not know. A provider endpoint with a
novel format, or a credential with an unrecognised prefix.

**What catches that failure:** layer 1.3.

### Layer 1.3: the profile format has no slot for a credential

A profile's declared path set passes two independent gates before any write.
The exempt bound rejects a path base has not registered as differing per
profile. The credential-name guard rejects any path whose last segment ends in
`TOKEN`, `KEY`, `SECRET`, `PASSWORD`, or `CREDENTIAL`, and any value carrying a
credential shape.

The two gates do not subsume each other. The exempt bound covers what somebody
registered, and the registry exempts `env.ANTHROPIC_AUTH_TOKEN`, so the bound
alone would let a token through. The credential guard covers what nobody
registered, and it has no notion of policy, so it alone would let a profile
overwrite `permissions.allow`.

**Catches:** a user writing a token into a profile, whatever the scan missed.

**Where it fails:** a credential that matches no shape and sits at a path
ending in none of those five words. A bare hexadecimal string at
`env.ANTHROPIC_BASE_URL` would pass.

**What catches that failure:** layer 1.4.

### Layer 1.4: the credential is never in a file the plugin manages

The credential lives in one file: the `apiKeyHelper`, outside the repository,
outside the plugin, and named by path. Contract clause 5 requires the resolved
path to sit outside every repository the plugin knows and outside the plugin
root, so the helper cannot be committed even by a user who tries.

**Catches:** every failure above at once, because a leak needs something to
leak and no file the plugin writes holds the secret.

**Where it fails:** the user puts the helper inside the repository anyway and
skips validation.

**What catches that failure:** nothing inside this plugin. Layer 1.1 still
applies to the helper's own path unless it lands in an allowlisted directory,
and clause 5 fires whenever validation runs. This is the floor, and the report
says so rather than claiming a fifth layer.

## Threat 2: a credential reaches a model's context

A settings file may hold `env.ANTHROPIC_AUTH_TOKEN`. Reading such a file into
a transcript publishes the token to a log, a session file, and whatever reads
them later.

### Layer 2.1: permission deny rules on the Read tool

`harness-setup.sh` merges these into `permissions.deny` in
`settings.base.json`, and the alignment sweep carries them into every variant.

```json
{
  "permissions": {
    "deny": [
      "Read(**/settings.json)",
      "Read(**/settings.*.json)",
      "Read(**/settings.local.json)",
      "Read(~/.claude/agents/**)",
      "Read(**/.claude/agents/**)",
      "Read(~/.claude/plugins/data/**)"
    ]
  }
}
```

`settings.base.json` is excluded from the deny list and stays readable,
because it is the tracked policy floor, `audit-base` precondition 3 requires
it to name nothing exempt, and the skill cannot do its job without it.

Agent definitions appear here because a custom agent carries its own settings
and so may carry a key.

The plugin data directory appears here because profile files name helper paths,
which are private paths even though they are not credentials.

**Catches:** the Read tool opening a settings file or an agent definition.

**Where it fails:** Bash. A `cat` or a `jq .` through Bash never reaches the
Read tool's permission check.

**What catches that failure:** layer 2.2, and outside this plugin the
PreToolUse hooks `settings.base.json` already registers, which the skill's own
text records as covering the Read tool and Bash alike. Those hooks belong to
concurrent work and this plugin adds none, so this model names them as an
existing layer rather than claiming them.

### Layer 2.2: every diagnostic reports key paths, never values

The pattern is one filter:

```bash
jq -r 'paths(scalars) | join(".")' "${settings_file}"
```

It reports which keys a settings file sets and reveals no value. Every
diagnostic this plugin ships uses it or an explicit non-credential subtree.

Three places need to compare values, and each avoids surfacing them:

| Comparison | How it avoids the value |
|------------|-------------------------|
| Is the active profile's endpoint the one in `settings.json`? | `harness-doctor.sh` hashes both sides with `shasum -a 256`, compares the hashes, and prints `match` or `differ`. A hash of an endpoint is not the endpoint. |
| Does `settings.json` already hold every path the profile declares? | Compares the two key-path sets, which carry no values. |
| Is a variant aligned with base? | `predicates.jq` returns violations. The `floor` predicate prints only base's own leaf pairs, and precondition 3 requires base to name nothing exempt, so those values are policy by construction. |

One change to `predicates.jq` follows from this rule. Its
`value-carries-no-locator` check printed the offending string, which is how an
endpoint or a private path would reach a transcript. It now prints a
classification instead:

```text
{ "locator": "url" }   rather than   { "locator": "https://internal.example/..." }
```

The check still fails, still names the path, and no longer carries the value.

**Catches:** a value reaching a transcript through a command the plugin ships.

**Where it fails:** a future script author writing `cat "${settings_file}"`.

**What catches that failure:** layer 2.3.

### Layer 2.3: a guard that lints the plugin's own scripts

`harness-guard.sh scripts` reads every `*.sh` and every `*.bats` file the
plugin ships and rejects a set of constructs:

| Construct | Why it is rejected |
|-----------|--------------------|
| `cat` applied to a settings path | Prints every value |
| `jq .` or `jq -r .` with no path filter, applied to a settings path | Prints every value |
| A command substitution around a variable named for the helper | Captures the credential |
| `paths(scalars)` absent from a script that names a settings file and prints from it | The value-free pattern is the required one |

This is enforcement rather than intent, because it runs in the test suite and
fails the suite.

**Catches:** a script added later that reads values.

**Where it fails:** a construct the guard does not know, spelled differently.

**What catches that failure:** review, and layer 2.1 for the Read tool path.
The report states this as the floor for threat 2.

## Threat 3: a credential is captured by running the helper

Running an `apiKeyHelper` produces a token on stdout. Whatever ran it holds
the token: a shell variable, a process's memory, a log line, a transcript.

### Layer 3.1: validation never executes

`harness-profile.sh validate` checks the helper's existence, its file type,
its executable bit, its mode's group and other digits, and that its resolved
path sits outside the repository and outside the plugin. Five checks, no
execution.

The consequence is stated rather than hidden: validation proves the helper is
installed and never that it works. A user learns it works when a session
authenticates.

**Catches:** the obvious mistake, a validator that runs the thing to see
whether it runs.

**Where it fails:** a script that shells out to the helper for another reason,
such as a diagnostic asking whether authentication would succeed.

**What catches that failure:** layer 3.2.

### Layer 3.2: no script names the helper in a command position

The helper's path lives in exactly one variable in exactly one script, and it
reaches only `[[ -e ]]`, `[[ -f ]]`, `[[ -x ]]`, `stat`, and a prefix
comparison. `harness-guard.sh scripts` rejects a command substitution or a
bare invocation around that variable.

**Catches:** a future author calling the helper.

**Where it fails:** an author who copies the path into a new variable name the
guard does not know.

**What catches that failure:** layer 3.3.

### Layer 3.3: the shipped template cannot authenticate

The template at `templates/api-key-helper.template.sh` writes a placeholder to
stdout and exits non-zero with a message on stderr. It ships without the
executable bit. Running it, deliberately or by accident, produces no
credential and no successful exit.

**Catches:** a template that ships working and gets committed with a real
value pasted into it, which is the most common way a helper leaks.

**Where it fails:** the user replaces the placeholder with a literal token
rather than a lookup.

**What catches that failure:** the template's own comment names the lookup
form, and layer 1.2's material scan finds a credential shape if the file ever
lands in a scanned directory. The helper's correct location is outside every
scanned directory, so this is the floor for threat 3.

## Threat 4: a test or a script touches real user state

### Layer 4.1: scripts reach the config directory only through an override

No script names `${HOME}/.claude` directly. Every one resolves
`${CLAUDE_CONFIG_DIR:-${HOME}/.claude}`, and the data directory through
`${HARNESS_CONFIG_DATA:-${CLAUDE_PLUGIN_DATA:-<config>/plugins/data/harness-config}}`.

A test exports both to a temporary directory before invoking anything. The
script then has no path to real state, so a test cannot reach it even by
mistake.

**Catches:** a test that would otherwise read or write the user's live
settings.

**Where it fails:** a test that forgets to export the overrides and so runs
against the real config directory.

**What catches that failure:** layer 4.2.

### Layer 4.2: a meta-test over the whole suite

One test reads every other test file and fails on any of these:

| Pattern | Why it fails the suite |
|---------|------------------------|
| `$HOME` or `${HOME}` outside the fixture builder | A test naming the real home may reach real state |
| `~/.claude` | The same, spelled with a tilde |
| A `Read` of an agent definition path | Agent definitions may carry a key |
| A settings path not under the test's temporary directory | The test reads real settings |

A reviewer confirms the property across the suite with one command, and it is
the meta-test itself:

```bash
bats features/harness-config/tests/guard-suite-hygiene.bats
```

The check that matters is not that it passes. It is that it fails when a
violation is planted, which the verification section of the final report
demonstrates by planting one.

**Catches:** a test file that skips the fixture discipline.

**Where it fails:** a test that reads real state through a path the meta-test
does not recognise, such as a variable assembled at runtime.

**What catches that failure:** layer 4.1, because the script under test still
resolves through the override and so reads the temporary directory regardless
of what the test names.

## The rules, and the one command that checks each

| Rule | The command a reviewer runs |
|------|----------------------------|
| No credential, private path, or account identifier in the plugin | `features/harness-config/scripts/harness-guard.sh material features/harness-config` |
| Every settings variant stays out of git, including names not yet used | `features/harness-config/scripts/harness-guard.sh ignore` |
| No shipped script reads settings values or runs a helper | `features/harness-config/scripts/harness-guard.sh scripts` |
| No test touches real user state | `bats features/harness-config/tests/guard-suite-hygiene.bats` |
| No `apiKeyHelper` script in the plugin | `find features/harness-config -name '*api*key*' -not -name '*.template.sh'`, which prints nothing |
| All four at once | `features/harness-config/scripts/harness-guard.sh all` |

## What this model does not cover

Four things sit outside it, and naming them is part of the model.

**The helper's own contents.** The plugin never reads the helper, so it cannot
tell whether the helper hardcodes a token or looks one up. Contract clause 6
states the requirement and declines to verify it.

**Bash reads of settings files.** The deny rules cover the Read tool. Bash
coverage belongs to the PreToolUse hooks `settings.base.json` already
registers, which concurrent work owns.

**`scripts/zai-api-key.sh` in this repository.** It is tracked today, because
`.gitignore` allowlists `scripts/**`. Structural counts taken without reading
it report zero inline credential prefixes and zero absolute `/Users` paths, so
no credential sits in git. A tracked `apiKeyHelper` is still the shape this
plugin forbids inside itself, and the plugin's material scan reports it when
pointed at the repository root. Moving it is the user's call, because the live
`settings.json` names it.

**A running session.** Activation writes `settings.json`, and the session that
ran it keeps the configuration it started with.
