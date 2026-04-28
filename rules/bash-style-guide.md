---
paths:
  - "**/*.sh"
  - "**/*.bash"
  - "**/*.zsh"
  - "**/*.bats"
  - "**/.bashrc"
  - "**/.bash_profile"
  - "**/.zshrc"
  - "**/.zshenv"
  - "**/.profile"
---

# Google Shell Style Guide

> **Source**: [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
>
> This document is a comprehensive reference copy of the Google Shell Style Guide, formatted as markdown. Refer to the original source for the latest version.

---

## Table of Contents

- [Background](#background)
  - [Which Shell to Use](#which-shell-to-use)
  - [When to use Shell](#when-to-use-shell)
- [Shell Files and Interpreter Invocation](#shell-files-and-interpreter-invocation)
  - [File Extensions](#file-extensions)
  - [SUID/SGID](#suidsgid)
- [Environment](#environment)
  - [STDOUT vs STDERR](#stdout-vs-stderr)
- [Comments](#comments)
  - [File Header](#file-header)
  - [Function Comments](#function-comments)
  - [Implementation Comments](#implementation-comments)
  - [TODO Comments](#todo-comments)
- [Formatting](#formatting)
  - [Indentation](#indentation)
  - [Line Length and Long Strings](#line-length-and-long-strings)
  - [Pipelines](#pipelines)
  - [Control Flow](#control-flow)
  - [Case Statement](#case-statement)
  - [Variable Expansion](#variable-expansion)
  - [Quoting](#quoting)
- [Features and Bugs](#features-and-bugs)
  - [ShellCheck](#shellcheck)
  - [Command Substitution](#command-substitution)
  - [Test, \[ ... \], and \[\[ ... \]\]](#test----and---)
  - [Testing Strings](#testing-strings)
  - [Wildcard Expansion of Filenames](#wildcard-expansion-of-filenames)
  - [Eval](#eval)
  - [Arrays](#arrays)
  - [Pipes to While](#pipes-to-while)
  - [Arithmetic](#arithmetic)
  - [Aliases](#aliases)
- [Naming Conventions](#naming-conventions)
  - [Function Names](#function-names)
  - [Variable Names](#variable-names)
  - [Constants, Environment Variables, and readonly Variables](#constants-environment-variables-and-readonly-variables)
  - [Source Filenames](#source-filenames)
  - [Use Local Variables](#use-local-variables)
  - [Function Location](#function-location)
  - [main](#main)
- [Calling Commands](#calling-commands)
  - [Checking Return Values](#checking-return-values)
  - [Builtin Commands vs. External Commands](#builtin-commands-vs-external-commands)
- [When in Doubt: Be Consistent](#when-in-doubt-be-consistent)

---

## Background

### Which Shell to Use

Bash is the only shell scripting language permitted for executables.

Scripts must begin with `#!/bin/bash` and use `set` for shell options to maintain functionality when invoked as `bash script_name`. This standardization ensures consistency across systems where bash is universally available, eliminating the need for POSIX-compatibility concerns.

The sole exception occurs when external constraints mandate alternatives, such as legacy operating systems or restricted execution environments requiring POSIX shell.

### When to use Shell

Shell should only be used for small utilities or simple wrapper scripts.

Shell remains appropriate when primarily orchestrating other utilities with minimal data manipulation. However, performance-critical applications warrant alternative languages.

Scripts exceeding 100 lines or employing non-straightforward control flow should be rewritten in structured languages immediately. Code maintainability beyond the original author should guide complexity assessments.

---

## Shell Files and Interpreter Invocation

### File Extensions

Executables may use `.sh` extensions or none:

- **With build rules**: Prefer `.sh` for source files (e.g., `foo.sh`) with build rules producing `foo`.
- **Direct PATH invocation**: Omit extensions, as users needn't know implementation language.
- **Other cases**: Either approach remains acceptable.

Libraries must carry `.sh` extensions and should never be executable.

### SUID/SGID

SUID and SGID are forbidden on shell scripts.

Security vulnerabilities make shell scripts unsuitable for SUID/SGID elevation. Employ `sudo` instead for privilege escalation.

---

## Environment

### STDOUT vs STDERR

Redirect error messages to STDERR exclusively, facilitating separation of normal operations from actual problems. A recommended error-reporting function:

```bash
err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}
```

---

## Comments

### File Header

Every file requires a top-level comment describing contents. Copyright notices and author information remain optional.

```bash
#!/bin/bash
#
# Perform hot backups of Oracle databases.
```

### Function Comments

Functions that lack obvious brevity, or any library function, require documentation detailing:

- Function purpose
- Global variables used/modified
- Arguments accepted
- Output destinations (STDOUT/STDERR)
- Return values beyond exit status

```bash
#######################################
# Cleanup files from the backup directory.
# Globals:
#   BACKUP_DIR
#   ORACLE_SID
# Arguments:
#   None
#######################################
function cleanup() {
  ...
}
```

### Implementation Comments

Annotate tricky, non-obvious, or important code sections. Avoid excessive commentary -- target complex algorithms and unusual patterns.

### TODO Comments

Use `TODO` (uppercase) followed by identifier (name, email, or username) indicating the person most familiar with the issue. These facilitate searchability and accountability.

```bash
# TODO(mrmonkey): Handle the unlikely edge cases (bug ####)
```

---

## Formatting

### Indentation

Indent 2 spaces. No tabs.

Maintain blank lines between code blocks for readability. The sole tab exception applies to `<<-` here-document bodies.

### Line Length and Long Strings

Maximum line length is 80 characters.

Strings exceeding this limit should use here-documents or embedded newlines where feasible. Unavoidably long items (file paths, URLs) may exceed limits when placed alone or in variables to preserve searchability.

```bash
# Preferred: here-document
cat <<END
I am an exceptionally long
string.
END

# Embedded newlines acceptable
long_string="I am an exceptionally
long string."

# Long file paths as variables
long_file="/i/am/an/exceptionally/loooooooooooooooooooooooooooooooooooong_file"
```

### Pipelines

Single-line pipelines remain on one line. Multi-line pipelines split at each pipe segment with pipes on newlines and 2-space indentation for continuation:

```bash
# Single line
command1 | command2

# Multiple lines
command1 \
  | command2 \
  | command3 \
  | command4
```

This distinction clarifies pipeline structure from regular command continuations. Comments must precede entire pipelines.

### Control Flow

Place `; then` and `; do` on the same line as `if`, `for`, `while`, `until`, or `select`. Position `else` on its own line with closing statements (`fi`, `done`) vertically aligned with opening statements.

```bash
local dir
for dir in "${dirs_to_cleanup[@]}"; do
  if [[ -d "${dir}/${SESSION_ID}" ]]; then
    log_date "Cleaning up old files in ${dir}/${SESSION_ID}"
    rm "${dir}/${SESSION_ID}/"* || error_message
  else
    mkdir -p "${dir}/${SESSION_ID}" || error_message
  fi
done
```

For loops should consistently include `in "$@"` for clarity.

### Case Statement

Indent alternatives 2 spaces. Single-line alternatives require space after closing parenthesis and before `;;`.

```bash
case "${expression}" in
  a)
    variable="..."
    some_command "${variable}" "${other_expr}" ...
    ;;
  absolute)
    actions="relative"
    another_command "${actions}" "${other_expr}" ...
    ;;
  *)
    error "Unexpected expression '${expression}'"
    ;;
esac
```

Simple commands may share lines with patterns and `;;`:

```bash
while getopts 'abf:v' flag; do
  case "${flag}" in
    a) aflag='true' ;;
    b) bflag='true' ;;
    f) files="${OPTARG}" ;;
    v) verbose='true' ;;
    *) error "Unexpected option ${flag}" ;;
  esac
done
```

### Variable Expansion

Prioritized guidelines:

1. Maintain consistency with existing code.
2. Quote variables.
3. Prefer `"${var}"` over `"$var"`.
4. Avoid braces for single-character shell specials/positional parameters unless necessary.
5. Use braces for all other variables.

```bash
# Recommended patterns
echo "Positional: $1" "$5" "$3"
echo "Specials: !=$!, -=$-, _=$_. ?=$?, #=$# *=$* @=$@ \$=$$ ..."
echo "many parameters: ${10}"

# Braces avoiding confusion
set -- a b c
echo "${1}0${2}0${3}0"

echo "PATH=${PATH}, PWD=${PWD}, mine=${some_var}"
```

**Important**: Braces in `${var}` do not constitute quoting -- double quotes remain necessary.

### Quoting

- Quote strings containing variables, command substitutions, spaces, or shell metacharacters unless careful unquoted expansion is required or the value represents a shell-internal integer.
- Use arrays for safe quoting of element lists, particularly command-line flags.
- Optionally quote shell-internal integer constants: `$?`, `$#`, `$$`, `$!`.
- Prefer quoting "word" strings over command options or pathnames.
- Understand pattern-matching quoting in `[[ ... ]]`.
- Use `"$@"` except where `$*` specifically serves purposes like string concatenation.

```bash
# Single quotes: no substitution
# Double quotes: substitution permitted

flag="$(some_command and its args "$@" 'quoted separately')"
echo "${flag}"

declare -a FLAGS
FLAGS=( --foo --bar='baz' )
readonly FLAGS
mybinary "${FLAGS[@]}"

# Internal integer variables may remain unquoted
if (( $# > 3 )); then
  echo "ppid=${PPID}"
fi

# Never quote literal integers
value=32

# Quote command substitutions even expecting integers
number="$(generate_number)"

# Prefer quoting words
readonly USE_INTEGER='true'

# Quote shell metacharacters
echo 'Hello stranger, and well met. Earn lots of $$$'
echo "Process $$: Done making \$\$\$."

# For "$@" vs $*: the former preserves arguments intact, preventing
# word splitting and empty argument loss
```

---

## Features and Bugs

### ShellCheck

The [ShellCheck](https://www.shellcheck.net/) project identifies common bugs and warnings. It is recommended for all scripts regardless of size.

### Command Substitution

Use `$(command)` over backticks:

```bash
# Preferred
var="$(command "$(command1)")"

# Not preferred
var="`command \`command1\``"
```

Backticks complicate nesting through escape requirements; `$(...)` syntax remains consistent when nested.

### Test, `[ ... ]`, and `[[ ... ]]`

`[[ ... ]]` is preferred over `[ ... ]`, `test` and `/usr/bin/[`.

`[[ ... ]]` prevents pathname expansion and word splitting, supports pattern/regex matching unavailable in `[ ... ]`, and generally reduces errors.

```bash
# Pattern/regex matching in [[ ... ]]
if [[ "filename" =~ ^[[:alnum:]]+name ]]; then
  echo "Match"
fi

# Exact pattern matching (doesn't expand f*)
if [[ "filename" == "f*" ]]; then
  echo "Match"
fi
```

Conversely, `[ ... ]` undergoes expansion and lacks `==` support (using only `=`).

### Testing Strings

Employ explicit string tests rather than filler characters where possible:

```bash
# Preferred: explicit test
if [[ "${my_var}" == "some_string" ]]; then
  do_something
fi

# Preferred: -z (zero length) and -n (non-zero length)
if [[ -z "${my_var}" ]]; then
  do_something
fi

# Acceptable but less preferred
if [[ "${my_var}" == "" ]]; then
  do_something
fi
```

Avoid filler characters like `"${my_var}X" == "some_stringX"`.

Use `-z` and `-n` explicitly for clarity:

```bash
# Use this
if [[ -n "${my_var}" ]]; then
  do_something
fi

# Instead of this
if [[ "${my_var}" ]]; then
  do_something
fi
```

Prefer `==` for equality (encourages `[[` usage); use `(( ... ))` or `-lt`/`-gt` for numerical comparisons:

```bash
# Equality in [[ ... ]]
if [[ "${my_var}" == "val" ]]; then
  do_something
fi

# Numerical comparison
if (( my_var > 3 )); then
  do_something
fi

if [[ "${my_var}" -gt 3 ]]; then
  do_something
fi
```

### Wildcard Expansion of Filenames

Expand wildcards with explicit paths (`./*`) rather than bare `*`:

```bash
# Safer: ./* prevents treating filenames as options
rm -v ./*

# Unsafe: treats -f and -r as options
rm -v *
```

### Eval

Avoid `eval`. It complicates variable assignment verification and enables unwanted variable sets:

```bash
# Problematic
eval $(set_my_variables)
variable="$(eval some_function)"
```

### Arrays

Use bash arrays for storing element lists, preventing quoting complications particularly with command arguments. Arrays maintain ordered string collections, safely expanding into individual elements.

```bash
# Arrays for command arguments
declare -a flags
flags=(--foo --bar='baz')
flags+=(--greeting="Hello ${name}")
mybinary "${flags[@]}"

# Avoid strings for sequences
flags='--foo --bar=baz'
flags+=' --greeting="Hello world"'  # Fails as intended
mybinary ${flags}
```

Command expansions produce strings, not arrays. Unquoted expansion in assignments risks failures with special characters or whitespace:

```bash
# Problematic: subject to expansion
declare -a files=($(ls /directory))

# Problematic: subject to expansion
mybinary $(get_arguments)
```

#### Arrays Pros

- Enable list handling without confusing quote nesting.
- Store arbitrary sequences including whitespace-containing strings.

#### Arrays Cons

- Risk increasing script complexity.

#### Arrays Decision

Arrays safely create and pass lists, particularly for command arguments, using quoted expansion `"${array[@]}"`. Advanced data manipulation demands non-shell languages.

### Pipes to While

Prefer process substitution or `readarray` (bash4+) over piping to `while`:

```bash
# Problematic: pipe creates subshell, variables don't propagate
last_line='NULL'
your_command | while read -r line; do
  if [[ -n "${line}" ]]; then
    last_line="${line}"
  fi
done
echo "${last_line}"  # Always outputs 'NULL'

# Preferred: process substitution
last_line='NULL'
while read line; do
  if [[ -n "${line}" ]]; then
    last_line="${line}"
  fi
done < <(your_command)
echo "${last_line}"  # Outputs last non-empty line

# Alternative: readarray
last_line='NULL'
readarray -t lines < <(your_command)
for line in "${lines[@]}"; do
  if [[ -n "${line}" ]]; then
    last_line="${line}"
  fi
done
echo "${last_line}"
```

For-loops iterating command output split by whitespace, not lines. Use `while read` or `readarray` for safer line iteration when output contains unexpected whitespace.

### Arithmetic

Use `(( ... ))` or `$(( ... ))` rather than `let`, `$[ ... ]`, or `expr`:

```bash
# Simple calculation in strings
echo "$(( 2 + 2 )) is 4"

# Arithmetic comparisons
if (( a < b )); then
  ...
fi

# Variable calculations
(( i = 10 * j + 400 ))
```

Avoid:

```bash
# Non-portable and deprecated
i=$[2 * 10]

# Subject to globbing/word-splitting
let i="2 + 2"

# External program, slower
i=$( expr 4 + 4 )
```

Built-in arithmetic vastly outperforms `expr`.

Within `$(( ... ))`, omit variable braces (`${var}`) for cleaner code -- the shell resolves variable names automatically:

```bash
local -i hundred="$(( 10 * 10 ))"
declare -i five="$(( 10 / 2 ))"

# Increment without ${i}
(( i += 3 ))

# Decrement without ${i}
(( i -= 5 ))

# Complex computation
hr=2
min=5
sec=30
echo "$(( hr * 3600 + min * 60 + sec ))"  # 7530
```

### Aliases

For almost every purpose, shell functions are preferred over aliases.

Aliases require careful quoting/escaping and prove difficult to debug:

```bash
# Problematic: $RANDOM evaluates at alias definition
alias random_name="echo some_prefix_${RANDOM}"

# Preferred: function
random_name() {
  echo "some_prefix_${RANDOM}"
}

# Function with arguments via $@
fancy_ls() {
  ls -lh "$@"
}
```

Functions provide alias functionality with superior robustness.

---

## Naming Conventions

### Function Names

Use lowercase with underscores separating words. Separate libraries with `::`. Parentheses remain required; the `function` keyword is optional but must stay consistent within projects.

```bash
# Single function
my_func() {
  ...
}

# Package function
mypackage::my_func() {
  ...
}
```

Braces must appear on the same line as function names with no space before parentheses. The `function` keyword enhances quick function identification despite being technically redundant with `()`.

### Variable Names

Follow function naming conventions. Loop variables should match looped content names:

```bash
for zone in "${zones[@]}"; do
  something_with "${zone}"
done
```

### Constants, Environment Variables, and readonly Variables

Capitalize constants and exported variables, separated by underscores, declared at file tops:

```bash
# Constant
readonly PATH_TO_FILES='/some/path'

# Constant and exported
declare -xr ORACLE_SID='PROD'
```

Alternatively, declare and export separately:

```bash
readonly PATH_TO_FILES='/some/path'
export PATH_TO_FILES
```

Constants may be assigned conditionally but must become readonly immediately afterward:

```bash
ZIP_VERSION="$(dpkg --status zip | sed -n 's/^Version: //p')"
if [[ -z "${ZIP_VERSION}" ]]; then
  ZIP_VERSION="$(pacman -Q --info zip | sed -n 's/^Version *: //p')"
fi
if [[ -z "${ZIP_VERSION}" ]]; then
  handle_error_and_quit
fi
readonly ZIP_VERSION
```

### Source Filenames

Use lowercase with underscores separating words if desired. Examples: `maketemplate` or `make_template`, never `make-template`.

### Use Local Variables

Declare function-specific variables via `local` to restrict scope and prevent global namespace pollution:

```bash
my_func2() {
  local name="$1"

  # Separate declaration from assignment with command substitution
  local my_var
  my_var="$(my_func)"
  (( $? == 0 )) || return

  ...
}
```

Avoid combining `local` declaration with command substitution assignment, as `local` exit code overwrites command status:

```bash
# Problematic: $? contains local's status, not my_func's
my_func2() {
  local my_var="$(my_func)"
  (( $? == 0 )) || return
  ...
}
```

### Function Location

Group all functions near file tops, immediately following constants. Never intersperse executable code among functions. Top-level organization should follow this order:

1. Includes
2. `set` statements
3. Constants
4. Functions
5. Main execution

### main

Scripts containing multiple functions require a `main` function serving as program entry point:

```bash
main() {
  # Program logic here
}

main "$@"
```

This convention improves code consistency, enables additional `local` variable declarations, and clearly marks program start. Short linear scripts bypass this requirement.

---

## Calling Commands

### Checking Return Values

Always verify return values with informative error handling:

```bash
# Preferred: direct if statement
if ! mv "${file_list[@]}" "${dest_dir}/"; then
  echo "Unable to move ${file_list[*]} to ${dest_dir}" >&2
  exit 1
fi

# Alternative: $? check
mv "${file_list[@]}" "${dest_dir}/"
if (( $? != 0 )); then
  echo "Unable to move ${file_list[*]} to ${dest_dir}" >&2
  exit 1
fi
```

For pipeline status checking, use `PIPESTATUS`:

```bash
tar -cf - ./* | ( cd "${dir}" && tar -xf - )
if (( PIPESTATUS[0] != 0 || PIPESTATUS[1] != 0 )); then
  echo "Unable to tar files to ${dir}" >&2
fi
```

Since `PIPESTATUS` gets overwritten by subsequent commands, preserve it immediately:

```bash
tar -cf - ./* | ( cd "${DIR}" && tar -xf - )
return_codes=( "${PIPESTATUS[@]}" )
if (( return_codes[0] != 0 )); then
  do_something
fi
if (( return_codes[1] != 0 )); then
  do_something_else
fi
```

### Builtin Commands vs. External Commands

Given the choice between invoking a shell builtin and invoking a separate process, choose the builtin.

Shell builtins surpass external processes in efficiency, robustness, and portability. Leverage Parameter Expansion and regex matching via `=~` operator:

```bash
# Preferred: builtins
addition="$(( X + Y ))"
substitution="${string/#foo/bar}"
if [[ "${string}" =~ foo:(\d+) ]]; then
  extraction="${BASH_REMATCH[1]}"
fi

# Avoid: external processes
addition="$(expr "${X}" + "${Y}")"
substitution="$(echo "${string}" | sed -e 's/^foo/bar/')"
extraction="$(echo "${string}" | sed -e 's/foo:\([0-9]\)/\1/')"
```

---

## When in Doubt: Be Consistent

Using one style consistently through our codebase lets us focus on other (more important) issues.

Consistency enables focus on meaningful concerns, facilitates automation, and resolves ambiguous style questions through established patterns. However, consistency should not justify perpetuating outdated approaches when newer styles demonstrate clear benefits. Codebases naturally converge toward contemporary styles over time.
