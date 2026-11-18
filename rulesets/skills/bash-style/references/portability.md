# Portability: bash 3.2 and stock tools

Read this where a script must run on macOS's `/bin/bash`, which is bash 3.2, or on both macOS and Linux.
Each form in the left column failed under `/bin/bash` 3.2.57 or under the tools macOS ships, and each form on the right ran there.

Check a script for these by running `/bin/bash -n <file>` and then its tests under `/bin/bash`, since shellcheck checks against the shebang's shell and reports none of the bash 3.2 gaps.

## Bash features absent from 3.2

| Absent | Write |
| --- | --- |
| associative array, `declare -A` | a `case` statement inside a function that maps a key to its value, or two indexed arrays walked together |
| `mapfile`, `readarray` | `while IFS= read -r line; do lines+=("${line}"); done < <(command)` |
| `${name,,}`, `${name^^}` | `tr '[:upper:]' '[:lower:]' <<<"${name}"`, or a `case` on the few values that matter |
| `&>>file` | `>>file 2>&1` |
| `a \|& b` | `a 2>&1 \| b` |
| `coproc` | a named pipe made with `mkfifo` |
| `shopt -s globstar` and `**` | `find <dir> -name '<pattern>'` read through a `while read` loop |
| `declare -g` | a plain assignment at file scope, or an assignment inside the function with no `local` |
| `printf '%(%Y)T'` | `date +%Y` |
| `local -n`, namerefs | print the result on stdout, or `printf -v "${name}" '%s' "${value}"` |
| `wait -n` | `wait <pid>` on each child |
| `${list[-1]}` | `"${list[${#list[@]}-1]}"` |
| `${name@Q}` | `printf '%q' "${name}"` |
| `$EPOCHSECONDS` | `date +%s` |
| `$BASHPID` | pass `$$` in, or read the child's PID from `$!` in the parent |
| `shopt -s inherit_errexit`, `shopt -s lastpipe` | check the command substitution's status on its own line, and feed loops by process substitution |
| `read -t 0.5`, a fractional timeout | a whole number |

## Behaviors that differ on 3.2

Expanding an empty array under `set -u` is an error on 3.2.
Write `${list[@]+"${list[@]}"}` wherever the array may be empty:

```bash
local -a extra=()
run_tool ${extra[@]+"${extra[@]}"} "${target}"
```

A failing `[[ ... ]]` or `(( ... ))` under `set -e` aborts on 3.2 only as the last command of its function.
Write the test as the condition of an `if`, or end it with `|| return 1`, wherever the script relies on it to stop.

## Forms 3.2 runs

These hold on 3.2 and need no replacement: indexed arrays and `+=`, `[[ ... =~ ... ]]` with `BASH_REMATCH`, process substitution `<(...)`, here-strings `<<<`, `printf -v`, `read -r -a`, `${!name}` indirection, `${name//pattern/replacement}`, `set -o pipefail`, and `local`.

## Tools: flags only GNU accepts

A stock macOS ships BSD tools.
Write the form both families accept wherever the script runs on macOS and Linux.

| GNU only | Write |
| --- | --- |
| `grep -P` | `grep -E`, or `[[ ... =~ ... ]]` |
| `sed -i 's/a/b/' file` | `sed 's/a/b/' file >"${scratch}" && mv "${scratch}" file` |
| `date -d '<string>'` | arithmetic on `date +%s`, or a value passed in |
| `stat -c '%s' file` | `wc -c <file` for a size, `[[ a -nt b ]]` for a comparison of ages |
| `head -n -1` | `sed '$d'` |
| `ln -sr` | `ln -s` with a path you build |
| `find ... -printf` | `find ... -exec basename {} \;`, or a `while read` loop over `find ... -print` |
| `readlink -f`, `realpath` on older systems | `cd "$(dirname "${path}")" && pwd -P` |

`wc -l` pads its number with spaces on macOS, so compare it with `-eq` inside `[[ ... ]]` or `(( ... ))`, never as a string.

## Tools a stock machine lacks

Detect each with `command -v` before use, and give the script a path that works without it or an error naming the tool.

- `timeout`, `nproc`, `setsid`, and `flock` are absent from a stock macOS.
- GNU `parallel`, `jq`, `shellcheck`, `shfmt`, and `bats` are absent from a stock macOS and from a minimal Linux image.
- Count cores with `nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1`.
- Bound a command without `timeout` by starting it in the background under `set -m` and killing its process group from a watcher, as the Error handling section of the skill describes.
