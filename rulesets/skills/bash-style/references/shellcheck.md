# ShellCheck findings and the change that clears each

Run shellcheck in the form the repository's hook runs it, with its `.shellcheckrc`, and plain `shellcheck <file>` where it has none.
Clear each finding by changing the code, never with a `disable` directive.
Each finding has a page at `https://www.shellcheck.net/wiki/SC<number>`.

## Common findings

| Code | It reports | Change |
| --- | --- | --- |
| SC2086 | an unquoted expansion the shell will split and glob | `"${name}"`; for several arguments held in one variable, an array expanded as `"${list[@]}"` |
| SC2046 | an unquoted command substitution | `"$(command)"`, or read its lines into an array |
| SC2068 | an unquoted `$@` or `${list[@]}` | `"$@"`, `"${list[@]}"` |
| SC2006 | backticks | `$(command)` |
| SC2155 | `local name="$(command)"`, which hides the command's status | `local name` on one line, `name="$(command)"` on the next |
| SC2164 | a `cd` whose failure is ignored | `cd "${dir}" \|\| exit` |
| SC2162 | `read` without `-r` | `read -r` |
| SC2181 | a check of `$?` after the fact | `if ! command; then` |
| SC2015 | `a && b \|\| c` used as if-then-else | an `if` statement |
| SC2064 | a trap in double quotes, expanded when set | single quotes, so it expands when the trap fires |
| SC2034 | a variable assigned and never read in this file | delete it; where another file reads it, `export` it or have that file source this one under a `source=` line |
| SC2154 | a variable read and never assigned in this file | pass the value as an argument, or source the file that assigns it under a `source=` line |
| SC1090 | a `source` of a path shellcheck cannot follow | a `# shellcheck source=<path>` line above it |
| SC1091 | a sourced file that was not given as input | `external-sources=true` and `source-path=SCRIPTDIR` in `.shellcheckrc`, with a `source=` line above the `source` |
| SC2148 | a file with no shebang | the shebang for an executable; `# shellcheck shell=bash` as the first line of a sourced file |

## Directives that stay

Two directives state a fact shellcheck cannot derive, and silence nothing:

```bash
# shellcheck shell=bash
# shellcheck source=lib/plan.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/plan.sh"
```

Directive reference: <https://www.shellcheck.net/wiki/Directive>

## A config that enforces more of this style

A repository's `.shellcheckrc` may turn on optional checks that hold scripts to this skill's forms.
Propose these where a repository has none, and add them only where the task asks:

```text
external-sources=true
source-path=SCRIPTDIR
enable=require-variable-braces
enable=quote-safe-variables
enable=require-double-brackets
enable=check-unassigned-uppercase
enable=add-default-case
```

List every optional check with `shellcheck --list-optional`.

## Bats files

ShellCheck reads `.bats` files and their `@test` blocks.
Two findings recur there, each with a change that clears it:

- SC2034 on `BATS_TEST_TIMEOUT=<n>` at file scope: write `export BATS_TEST_TIMEOUT=<n>`.
- SC2016 on a stub written with `printf` from single-quoted lines: write the stub through a here-document with a quoted delimiter, `<<'EOF'`.

## What shellcheck does not report

ShellCheck checks against the shell the shebang names and knows nothing of a version pin.
A form bash 3.2 rejects passes it.
Run `bash -n <file>` and the tests under the pinned bash for that, and read `portability.md`.
