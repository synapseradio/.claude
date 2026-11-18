---
name: bash-style
description: >-
  Load this before you write, change, or review any bash or shell file: a script, a sourced library, a git hook, a bats helper. It holds the mandatory bash style: structure, quoting, error handling, functions, naming, bash 3.2 portability, and shellcheck.
---

# Bash style

For every bash or shell file you write, change, or review, optimize for a script that runs what its text names on the oldest bash its repository targets, passes shellcheck with no finding silenced, and reads like the scripts beside it.

This binds every shell file at any length: an executable script, a sourced library, a git hook or other extensionless shell file, and the setup code, helpers, and stubs of a bats suite.
A file another shell also sources, a zsh startup file for one, follows the library rules below and the section on files two shells source.

The style distills Google's shell style guide at <https://google.github.io/styleguide/shellguide.html>, adjusted for bash 3.2 and shellcheck. Read it for the rationale behind a rule here.

## Notation

- `A -> B`: step A then step B of one instruction
- guard block: a name line then `| condition = act` lines, the first that fits taken and `otherwise` last

## Skills to load beside this one

Load `bats-testing` before writing, changing, running, or judging a test of the file.

## Before the first line

Read what the repository pins for shell, in its CI and hook configs, its manifest scripts, its `.shellcheckrc`, and the scripts beside the file in scope:

- the bash its scripts run on
- the linter and the formatter, with their flags and config
- the command that runs its shell tests

Follow each pin, and match the conventions the surrounding scripts hold.
Where two forms both fit this skill, take the one the surrounding scripts hold.
Treat consistency as no ground for keeping a form this skill rules out.

bash version
  | a pin names one = write for it
  | the repository's docs or CI name platforms = write for the oldest bash among them, which on macOS is `/bin/bash` 3.2
  | otherwise = write for the version `/bin/bash --version` reports on this machine

A `#!/usr/bin/env bash` shebang leaves the target where those rules put it, since `env` runs whichever bash comes first on `PATH`.
Where that version is 3.2, or the script runs on both macOS and Linux, read `references/portability.md` before writing.
It lists the bash features 3.2 lacks, the tool flags only GNU accepts, and the tools a stock machine lacks, each with the form to write.
Where a script runs only under a newer bash, in CI alone for one, keep old-bash forms and guards out of it and out of its tests.

Write for a stock machine unless a pin says otherwise: bash 3.2, the tools the system ships, and no tool a developer installs.
Detect each tool beyond those with `command -v` before the script uses it, and give the script a path that works without it or an error that names it.

language
  | external constraints mandate POSIX sh, as a legacy system or a restricted runtime may = write POSIX sh, and apply the rest of this skill only where it names forms sh accepts
  | the job needs a data structure beyond a string, an array, and, where the pinned bash is 4 or later, an associative array = write it in another language
  | the job needs control flow beyond a branch, a loop, and a function call = write it in another language
  | the job is performance critical, or runs to more than about 100 lines of logic = write it in another language
  | otherwise = bash

## A tool is missing

Assume none of the checking tools is installed.
Detect each with `command -v` before the first check: `shellcheck`, the formatter the repository pins such as `shfmt`, and the pinned bash.

Install nothing on your own.
Where a tool is missing or older than the repository's config needs, ask whether you may install it, in one question that gives:

- what is missing or too old, with the version found
- why the work needs it, such as the hook that runs it
- the exact command you would run
- what that command changes on the machine

command
  | the repository has a setup step that installs it, a `just tools` or an onboard script for one = that step
  | macOS with Homebrew = `brew install shellcheck`, `brew install shfmt`
  | Debian or Ubuntu = `sudo apt-get install shellcheck`, and for a formatter the package the distribution's search names
  | otherwise = the install line the tool's own documentation gives for the platform

Install only after a yes, with the command you showed, then detect again.

declined
  | shellcheck is missing = run `bash -n <file>` under the pinned bash, read the file against `references/shellcheck.md` by hand, and report that shellcheck did not run
  | the formatter is missing = format by the Formatting section below, and report that the formatter did not run

## File layout

Write a file in this order: the shebang, a header comment saying what the file does, the `source` lines, the `set` line, constants, functions, and the entry call.
Keep every function together below the constants, with no executable code between them.

```bash
#!/bin/bash
#
# Print the newest release tag of the current repository.

set -euo pipefail

readonly TAG_PREFIX='v'

err() {
  printf '%s\n' "$*" >&2
}

#######################################
# Print the newest tag that carries the release prefix.
# Globals:
#   TAG_PREFIX
# Outputs:
#   The tag, on stdout.
# Returns:
#   1 when no such tag exists.
#######################################
newest_tag() {
  local tag
  tag="$(git describe --tags --abbrev=0 --match "${TAG_PREFIX}*")" || return 1
  printf '%s\n' "${tag}"
}

main() {
  if ! newest_tag; then
    err 'no release tag found'
    exit 1
  fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
```

Open an executable on `#!/bin/bash`, or on the shebang the scripts beside it use.
Set shell options through a `set` line, never through shebang flags, so the script behaves the same run as `bash <script>`.
Keep the SUID and SGID bits off every shell script, and reach privilege through `sudo` inside it.
Give every script that defines more than one function a `main`, called on the last line with `"$@"`.
Wrap that call in the `BASH_SOURCE` guard above wherever a test sources the file, so sourcing defines the functions and runs nothing.

A library is a file other files source.
Give it a `.sh` extension and no executable bit, and keep `set` lines, `exit`, and top-level commands out of it, since each would act on the shell that sources it.
Split a long script into a thin entry file that sources libraries, sets options, and calls one function, with each library holding one concern.
Source a library by a path built from the sourcing file's own location, under a directive that tells shellcheck where it is:

```bash
# shellcheck source=lib/plan.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/plan.sh"
```

## A file two shells source

A file that both bash and zsh source, such as a shell startup file, takes only syntax both shells accept.
Probe in it for a function with `declare -f <name>`, and keep `declare -F` and `typeset -F` out.
Test it under both shells: write a scratchpad script that sources the file, then run that script as `zsh <script>` and as `bash <script>`, and read what each prints to stderr.

## Error handling

Open every executable with `set -euo pipefail`, and add `-E` where the script sets an `ERR` trap.
Then check every command whose failure matters anyway, because `set -e` does not act in these places:

- inside the condition of `if`, `while`, or `until`, and in every function called from one
- on any command of an `&&` or `||` list but the last, and in every function called from one
- on a command negated with `!`
- inside a command substitution, which runs without `-e`
- on `local name="$(command)"` and `export name="$(command)"`, whose status is that of `local` or `export`
- on bash 3.2, on a failing `[[ ... ]]` or `(( ... ))` that is not the last command of its function

Check a command by branching on it directly:

```bash
if ! mv "${source}" "${target}"; then
  err "cannot move ${source}"
  exit 1
fi
```

Write `<command> || return` or `<command> || exit` for a one-line check.
Keep `<a> && <b> || <c>` out as a stand-in for `if`, since `<c>` also runs when `<b>` fails.
Follow every `cd`, `pushd`, and `popd` with `|| exit` or `|| return`.
Copy `PIPESTATUS` into an array on the line after the pipeline where more than the last status matters, since the next command overwrites it.

Send every error and diagnostic to stderr, through one `err` function, and keep stdout for the output a caller reads.
Exit non-zero on every failure, and give each failure a caller tells apart its own status.

Clean up through a trap, set right after the resource exists, with its command in single quotes so it expands when it fires:

```bash
scratch="$(mktemp -d)" || exit 1
trap 'rm -rf "${scratch}"' EXIT
```

Where a script enforces a deadline on a child, kill the child's whole process group.
Start the child under `set -m`, which makes it the leader of its own group, and signal the group with a negative PID, as `kill -- "-${child}"`.
A kill aimed at the child's PID alone leaves its own children running, and each keeps holding the caller's file descriptors.

## Quoting and expansion

Quote every expansion: `"${name}"`, `"$(command)"`, `"$@"`.
Leave unquoted only a literal integer, the inside of `(( ... ))`, the right side of `=~`, and a pattern meant as a glob on the right of `==` inside `[[ ... ]]`.

Write single quotes where nothing expands and double quotes where something does.
Write `"${name}"` with braces for every variable, and `$1`, `$?`, `$#`, `$@` without them except where a following character would join the name.
Write `${10}` and every higher positional parameter with braces.
Pass arguments on as `"$@"`, and write `"$*"` only where one joined string is the point.
Write `$(command)`, never backticks.

Hold every list in an array, a list of command arguments above all, and expand it as `"${list[@]}"`:

```bash
local -a flags=(--quiet --output "${target}")
curl "${flags[@]}" "${url}"
```

Keep a list out of a space-separated string, and keep command output out of an unquoted `$(...)` that the shell would split.
Start a glob that expands to files with `./`, as `./*`, so a file named like an option stays a file.
Keep `eval` out.

## Tests and arithmetic

Write `[[ ... ]]` for every test, with `==` for string equality, `-z` and `-n` for emptiness, and `=~` for a regular expression.
Test emptiness with `-z` or `-n` explicitly, never as a bare `[[ "${name}" ]]` and never by padding both sides with a filler character.
Write `(( ... ))` for a numeric comparison and `$(( ... ))` for arithmetic, with `let`, `$[ ]`, and `expr` kept out, and write names inside them without `${}`.
Keep `(( count++ ))` out as a statement under `set -e`, since it returns failure when the value before the increment is 0, and write `count=$(( count + 1 ))`.
Give every `case` a `*)` arm.

## Loops over input

Read lines with `while IFS= read -r line`, fed by process substitution or a file:

```bash
while IFS= read -r line; do
  total=$(( total + 1 ))
done < <(list_items)
```

Keep `<command> | while read` out wherever the loop sets a variable, since a pipe runs the loop in a subshell and the variable is lost.
Keep `for word in $(command)` out, since it splits on every space.
Pass `-r` to every `read`.

## Functions

Declare a function as `name() {`.
Declare every variable a function uses with `local`.
Declare and assign on separate lines wherever the value comes from a command, so the command's status survives:

```bash
local version
version="$(read_version)" || return 1
```

Return a result on stdout, or a verdict as the exit status.
Where a function must set a global, name that global in its comment.
Give a function a comment block, in the form the layout above shows, where it belongs to a library or its use is not obvious from its name: what it does, the globals it reads or sets, its arguments, its output, and its statuses beyond 0.
Write a function in place of an alias.
Prefer a builtin to an external command: a parameter expansion such as `"${path##*/}"` over `basename`, and `[[ ... =~ ... ]]` with `BASH_REMATCH` over `sed` or `expr`.

## Naming

- a function or a variable: `lower_snake_case`
- a library function: `module::name`, with the file's name as the module
- a constant or an exported variable: `UPPER_SNAKE_CASE`, declared at the top of the file with `readonly` or `export`
- a loop variable: the singular of what it loops over, as `for zone in "${zones[@]}"`
- a file: the form the files beside it hold, and otherwise kebab-case for an executable, with no extension where people run it from `PATH`, and lower_snake_case with `.sh` for a library

Make a constant whose value comes from a command `readonly` on the line after its assignment.

## Formatting

Let the formatter the repository pins decide, and where it pins none:

- indent 2 spaces, with tabs only in the body of a `<<-` here-document
- separate blocks with a blank line
- keep lines within 80 characters, a long path or URL excepted, and put a long string in a here-document or break it with embedded newlines
- put `; then` and `; do` on the line of their `if`, `for`, or `while`
- put `else` on its own line, and align `fi` and `done` under their opener
- spell out `in "$@"` on a `for` over the arguments
- break a pipeline that does not fit one line before each `|`, indented 2 spaces, and put a comment above the whole pipeline, never between its segments
- indent each `case` alternative 2 spaces, and write an arm on one line as `pattern) command ;;` where it fits, and otherwise the pattern, the body, and `;;` on lines of their own

## Checks before a commit

Run on every file you changed, in the form the repository's hooks run them:

1. `bash -n <file>` under the pinned bash, so a form that bash rejects fails here.
2. shellcheck with the repository's config, until it reports nothing.
3. the pinned formatter.
4. the tests that cover the file, as `bats-testing` directs.

Clear every shellcheck finding by changing the code.
Keep every `# shellcheck disable=` line out of every file, and out of `.shellcheckrc`.
A `# shellcheck source=<path>` line and a `# shellcheck shell=bash` line state a fact shellcheck cannot see, and stay.
Read `references/shellcheck.md` for the change that clears each common finding, and <https://www.shellcheck.net/wiki/> for any other, at `https://www.shellcheck.net/wiki/SC<number>`.

Where a form here and the behavior of the pinned bash disagree, the bash manual settles it: <https://www.gnu.org/software/bash/manual/bash.html>.
