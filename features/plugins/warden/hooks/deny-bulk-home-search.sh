#!/bin/bash
#
# PreToolUse hook for the Bash, Grep, and Glob tools.
#
# Refuses a file search rooted at the filesystem root, at the directory that
# holds home directories, or at a home directory itself: find, fd, rg, ag,
# ack, a recursive grep, tree, du, a recursive or globbed ls, locate, an
# unscoped mdfind, and the Grep and Glob tools. A search scoped to a directory
# inside a home directory runs untouched.
#
# A search that names no root starts in the working directory, and a relative
# root resolves against it, so `find .` run from a home directory is refused
# and `find ..` run from one level below it is refused too.
#
# The roots are the usual home layouts on macOS and Linux plus the hook's own
# $HOME, so nothing here names a directory particular to one machine.
#
# Stdin:  PreToolUse hook JSON envelope.
# Stdout: hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:   0 in all cases (deny is communicated via stdout, not exit code).
# Sourced: defines decide_bash, decide_grep, decide_glob, and main, and runs
# none.

# Single quotes are intentional throughout: these regexes match the literal
# characters `$HOME` and `${HOME}` in a command, not their expansion.
# shellcheck disable=SC2016
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -euo pipefail
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/decision.sh
source "${SCRIPT_DIR}/lib/decision.sh"

# A home directory, the directory holding them, or a root's own spelling.
readonly NAMED_ROOT='(~|\$HOME|\$\{HOME\}|/(Users|home)(/[^/*?[]+)?|/root)'

# Options whose next word is a value rather than a search root, across the
# search tools handled below.
readonly VALUE_OPTIONS=' -g --glob --iglob -t --type -T --type-not --type-add -e --regexp -f --file -m --max-count -A -B -C -M --max-columns --max-depth --maxdepth -d --exact-depth -E --exclude -j --threads --max-filesize -L -I -P --pattern --ignore-dir --include --exclude-dir '

# Set by each decision function from the tool input.
CWD=''
BARE_RE=''
GLOB_RE=''

#######################################
# Record a deny decision.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - what was searched, quoted back in the reason.
#######################################
deny() {
  decision::reach deny "Refused: this search walks a whole home directory or the whole disk (${1}). Search inside the one directory that holds the target, or read the tool's documentation for the answer."
}

#######################################
# Escape every regex metacharacter in a string.
# Arguments:
#   $1 - the literal text.
# Outputs:
#   The escaped text on stdout.
#######################################
escape_regex() {
  local text="$1" out='' char index
  for ((index = 0; index < ${#text}; index++)); do
    char="${text:index:1}"
    case "${char}" in
    [\\^\$.\[\]\|\(\)\*\+\?\{\}]) out+="\\${char}" ;;
    *) out+="${char}" ;;
    esac
  done
  printf '%s\n' "${out}"
}

#######################################
# Build the two root regexes from NAMED_ROOT and $HOME.
# Globals:
#   HOME, BARE_RE, GLOB_RE
#######################################
build_root_patterns() {
  local root="${NAMED_ROOT}" home="${HOME:-}"
  home="${home%/}"
  if [[ -n "${home}" ]]; then
    root="(${NAMED_ROOT}|$(escape_regex "${home}"))"
  fi
  # A root on its own, with or without trailing slashes, or / itself.
  BARE_RE="^(${root}/*|/+)\$"
  # A glob in the first segment below a root, as in ~/* or /Users/*/x.
  GLOB_RE="^${root}?/+([*?[]|\\.[*?[]).*\$"
}

#######################################
# Collapse . and .. segments in an absolute path.
# Arguments:
#   $1 - the path.
# Outputs:
#   The normalized path on stdout.
#######################################
normalize_path() {
  local path="$1" segment out=''
  local -a segments
  IFS='/' read -r -a segments <<<"${path}"
  for segment in ${segments[@]+"${segments[@]}"}; do
    case "${segment}" in
    '' | .) ;;
    ..) out="${out%/*}" ;;
    *) out="${out}/${segment}" ;;
    esac
  done
  printf '%s\n' "${out:-/}"
}

#######################################
# Resolve a search root against the working directory. Roots already
# written from /, ~, or $HOME pass through as written.
# Globals:
#   CWD
# Arguments:
#   $1 - the root as written.
# Outputs:
#   The root to test on stdout.
#######################################
resolve_root() {
  local root="$1"
  case "${root}" in
  /* | '~'* | '$'*) printf '%s\n' "${root}" ;;
  *)
    if [[ -n "${CWD}" ]]; then
      normalize_path "${CWD}/${root}"
    else
      printf '%s\n' "${root}"
    fi
    ;;
  esac
}

#######################################
# Test whether a root is broad: a bare root, or a glob just below one.
# Arguments:
#   $1 - the root.
#######################################
is_broad() {
  [[ -n "$1" ]] || return 1
  [[ "$1" =~ ${BARE_RE} || "$1" =~ ${GLOB_RE} ]]
}

#######################################
# Test whether the working directory is broad.
# Globals:
#   CWD
#######################################
cwd_is_broad() {
  [[ -n "${CWD}" ]] && is_broad "$(normalize_path "${CWD}")"
}

#######################################
# Test whether grep's flags make it recursive.
# Arguments:
#   The words after the command name.
#######################################
grep_is_recursive() {
  local word
  for word in "$@"; do
    case "${word}" in
    --recursive | --dereference-recursive | --directories=recurse) return 0 ;;
    --*) ;;
    -*[rR]*) return 0 ;;
    esac
  done
  return 1
}

#######################################
# Test whether ls or one of its successors lists recursively.
# Arguments:
#   $1 - the command name.
#   The rest - the words after it.
#######################################
ls_is_recursive() {
  local command="$1" word
  shift
  for word in "$@"; do
    case "${word}" in
    --recursive | --tree) return 0 ;;
    --*) ;;
    -*R*) return 0 ;;
    -*T*) [[ "${command}" != ls && "${command}" != gls ]] && return 0 ;;
    esac
  done
  return 1
}

#######################################
# Check one search command's words and deny when it searches broadly.
# Globals:
#   VALUE_OPTIONS, GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the command name.
#   $2 - 1 when the first positional word is a pattern, not a root.
#   The rest - the words after the command name.
#######################################
check_search() {
  local command="$1" pattern_first="$2" word skip=0 positional=0 roots=0
  local stop_at_expression=0 resolved
  shift 2
  [[ "${command}" == find || "${command}" == gfind ]] && stop_at_expression=1

  for word in "$@"; do
    if ((skip)); then
      skip=0
      continue
    fi
    if ((stop_at_expression)) && [[ "${word}" == -* || "${word}" == '(' || "${word}" == '!' ]]; then
      break
    fi
    case "${word}" in
    -e | --regexp | -f | --file) pattern_first=0 ;;
    esac
    if [[ "${word}" == -* ]]; then
      [[ "${VALUE_OPTIONS}" == *" ${word} "* ]] && skip=1
      continue
    fi
    positional=$((positional + 1))
    if is_broad "${word}"; then
      deny "${command} ${word}"
      return 0
    fi
    if ((pattern_first && positional == 1)); then
      continue
    fi
    roots=$((roots + 1))
    resolved="$(resolve_root "${word}")"
    if is_broad "${resolved}"; then
      deny "${command} ${word}, which resolves to ${resolved}"
      return 0
    fi
  done

  if ((roots == 0)) && cwd_is_broad; then
    deny "${command} with no root, run in ${CWD}"
  fi
}

#######################################
# Check one command of a shell line.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the command text, already split from its neighbors.
#######################################
check_segment() {
  local -a words
  local count index=0 command word only_in='' next=0
  IFS=$' \t' read -r -a words <<<"$1"
  count=${#words[@]}

  # Step past assignments and the words that only run the next command.
  while ((index < count)); do
    word="${words[index]}"
    case "${word}" in
    -*) break ;;
    *=*) index=$((index + 1)) ;;
    sudo | command | time | nice | env | exec | builtin | then | do | else | '{' | '!' | xargs) index=$((index + 1)) ;;
    *) break ;;
    esac
  done
  ((index < count)) || return 0

  command="${words[index]##*/}"
  words=("${words[@]:index+1}")
  set -- ${words[@]+"${words[@]}"}

  case "${command}" in
  locate | plocate | mlocate | glocate)
    deny "${command} reads an index of the whole disk"
    ;;
  mdfind)
    for word in "$@"; do
      if ((next)); then
        only_in="${word}"
        next=0
      fi
      [[ "${word}" == -onlyin ]] && next=1
    done
    if [[ -z "${only_in}" ]] || is_broad "$(resolve_root "${only_in}")"; then
      deny "mdfind outside one directory"
    fi
    ;;
  find | gfind | tree | du | dust | ncdu)
    check_search "${command}" 0 "$@"
    ;;
  fd | fdfind | rg | ag | ack)
    check_search "${command}" 1 "$@"
    ;;
  grep | egrep | fgrep | ggrep | ugrep)
    if grep_is_recursive "$@"; then
      check_search "${command}" 1 "$@"
    fi
    ;;
  ls | gls | eza | exa | lsd)
    for word in "$@"; do
      [[ "${word}" == -* ]] && continue
      if [[ "${word}" =~ ${GLOB_RE} ]]; then
        deny "${command} ${word}"
        return 0
      fi
    done
    if ls_is_recursive "${command}" "$@"; then
      check_search "${command}" 0 "$@"
    fi
    ;;
  esac
}

#######################################
# Split a shell line into commands and check each one, stopping at the
# first that denies.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the shell line.
#######################################
check_command() {
  local text="$1" separator line
  text="${text//\"/}"
  text="${text//\'/}"
  for separator in '|' ';' '&' '(' ')' '`'; do
    text="${text//"${separator}"/$'\n'}"
  done
  while IFS= read -r line; do
    check_segment "${line}"
    ! decision::reached || return 0
  done <<<"${text}"
}

#######################################
# Check a Grep or Glob tool call.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the tool name.
#   $2 - the path argument, possibly empty.
#   $3 - the Glob pattern, empty for Grep.
#######################################
check_tool() {
  local tool="$1" path="$2" pattern="$3" base
  if [[ -z "${path}" ]]; then
    base="${CWD}"
  else
    base="$(resolve_root "${path}")"
  fi
  [[ -n "${base}" ]] && base="$(normalize_path "${base}")"

  case "${pattern}" in
  /* | '~'*)
    if is_broad "${pattern}"; then
      deny "${tool} ${pattern}"
    fi
    return 0
    ;;
  esac

  if [[ "${tool}" == Grep ]]; then
    if is_broad "${base}"; then
      deny "Grep in ${base}"
    fi
    return 0
  fi
  if is_broad "${base}" && [[ "${pattern}" == *'**'* || "${pattern}" == */* ]]; then
    deny "Glob ${pattern} in ${base}"
  fi
  return 0
}

#######################################
# Decide on a command the Bash tool proposes.
# Globals:
#   CWD, GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the command.
#   $2 - the session's working directory, possibly empty or absent.
#######################################
decide_bash() {
  decision::clear
  CWD="${2:-}"
  build_root_patterns
  check_command "$1"
}

#######################################
# Decide on a call of the Grep tool. Grep's pattern is a regex over file
# contents, never a path, so only the path is judged.
# Globals:
#   CWD, GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the path argument, possibly empty.
#   $2 - the session's working directory, possibly empty.
#######################################
decide_grep() {
  decision::clear
  CWD="$2"
  build_root_patterns
  check_tool Grep "$1" ''
}

#######################################
# Decide on a call of the Glob tool.
# Globals:
#   CWD, GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the Glob pattern.
#   $2 - the path argument, possibly empty.
#   $3 - the session's working directory, possibly empty.
#######################################
decide_glob() {
  decision::clear
  CWD="$3"
  build_root_patterns
  check_tool Glob "$2" "$1"
}

main() {
  local input tool_name cwd
  input="$(cat)"
  tool_name="$(jq -r '.tool_name // ""' <<<"${input}")"
  cwd="$(jq -r '.cwd // ""' <<<"${input}")"

  case "${tool_name}" in
  Bash)
    decide_bash "$(jq -r '.tool_input.command // ""' <<<"${input}")" \
      "${cwd}"
    ;;
  Grep)
    decide_grep "$(jq -r '.tool_input.path // ""' <<<"${input}")" "${cwd}"
    ;;
  Glob)
    decide_glob \
      "$(jq -r '.tool_input.pattern // ""' <<<"${input}")" \
      "$(jq -r '.tool_input.path // ""' <<<"${input}")" "${cwd}"
    ;;
  *)
    return 0
    ;;
  esac
  decision::print
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
