#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Denies a bunx or bun x command whose package argument names no version.
# bunx resolves the package from a registry and runs it in the same step, so
# a bare name runs whatever the registry serves at that moment. A version
# (name@1.2.3) or a tag (name@latest) is accepted.
#
# The package is the first word after bunx, or after bun x, that is not an
# option. Options that take a value have that value skipped, except -p and
# --package, whose value is the package: when one or more appear, those
# values are judged and the word after the options is left alone, since it
# then names a binary. A scoped package's leading @ does not separate a
# version, so @scope/pkg names none and @scope/pkg@2.0.1 names one.
#
# A program counts when it stands at a command position, as the splitting in
# lib/command_words.sh defines it, so the name inside a quoted argument is
# silent. A command with no package argument, such as bunx --version, is
# silent.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when staying silent.
# Exit:    0 in all cases (the decision travels on stdout, not the exit code).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"

# Options, besides -p and --package, whose next word is a value rather than
# the package.
readonly VALUE_OPTIONS=' --cwd -c --config --registry --install '

# The bunx arguments of the program line under inspection, set by
# collect_bunx_args.
BUNX_ARGS=()

# The first package argument found to name no version, set by find_unpinned.
UNPINNED=''

#######################################
# Report whether a package argument names a version or a tag.
# Arguments:
#   $1 - the package argument.
# Returns:
#   0 when a non-empty version follows an @ that is not a scope marker.
#######################################
names_version() {
  local rest="$1"
  if [[ "${rest}" == @* ]]; then
    rest="${rest:1}"
  fi
  [[ "${rest}" == *@?* ]]
}

#######################################
# Collect the arguments of bunx when a program line is a bunx run.
# Globals:
#   VALUE_OPTIONS, BUNX_ARGS
# Arguments:
#   The program's name, then its arguments.
# Returns:
#   0 for bunx or bun x, 1 otherwise.
#######################################
collect_bunx_args() {
  local program="$1" word skip=0
  shift
  BUNX_ARGS=()

  case "${program}" in
  bunx)
    BUNX_ARGS=("$@")
    return 0
    ;;
  bun)
    for word in "$@"; do
      if ((skip)); then
        skip=0
        shift
        continue
      fi
      if [[ "${word}" == -* ]]; then
        if [[ "${VALUE_OPTIONS}" == *" ${word} "* ]]; then
          skip=1
        fi
        shift
        continue
      fi
      if [[ "${word}" == x ]]; then
        shift
        BUNX_ARGS=("$@")
        return 0
      fi
      return 1
    done
    ;;
  esac
  return 1
}

#######################################
# Find the first package argument among bunx's arguments that names no
# version.
# Globals:
#   VALUE_OPTIONS, UNPINNED
# Arguments:
#   The bunx arguments.
#######################################
find_unpinned() {
  local word candidate skip=0 expect_package=0 first=''
  local -a named=()
  UNPINNED=''

  for word in "$@"; do
    if ((expect_package)); then
      named+=("${word}")
      expect_package=0
      continue
    fi
    if ((skip)); then
      skip=0
      continue
    fi
    case "${word}" in
    -p | --package)
      expect_package=1
      ;;
    --package=*)
      named+=("${word#--package=}")
      ;;
    -*)
      if [[ "${VALUE_OPTIONS}" == *" ${word} "* ]]; then
        skip=1
      fi
      ;;
    *)
      first="${word}"
      break
      ;;
    esac
  done

  if ((${#named[@]} == 0)); then
    if [[ -n "${first}" ]]; then
      named=("${first}")
    else
      return 0
    fi
  fi

  for candidate in "${named[@]}"; do
    if ! names_version "${candidate}"; then
      UNPINNED="${candidate}"
      return 0
    fi
  done
}

#######################################
# Emit a deny decision naming the unpinned package.
# Globals:
#   UNPINNED
# Outputs:
#   The permission decision JSON on stdout.
#######################################
deny() {
  local reason
  reason="bunx runs ${UNPINNED} with no version, so it fetches whatever the registry serves at that moment and executes it. Run bunx at a pinned version or @latest: bunx <pkg>@<version>. Before it runs, state in the message: the package, the version the command pins, what it executes, and which installed tool falls short of the step."
  jq -nc --arg r "${reason}" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

main() {
  local command line
  local -a words
  command="$(jq -r '.tool_input.command // ""')"

  if [[ -z "${command}" ]]; then
    return 0
  fi

  while IFS= read -r line; do
    IFS=' ' read -r -a words <<<"${line}"
    if collect_bunx_args "${words[@]}"; then
      find_unpinned ${BUNX_ARGS[@]+"${BUNX_ARGS[@]}"}
      if [[ -n "${UNPINNED}" ]]; then
        deny
      fi
    fi
  done < <(command_words::resolve "${command}")

  return 0
}

main "$@"
