#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Prompts (permissionDecision: "ask") when a command runs a shell with -c:
# bash, sh, zsh, dash, or ksh, with -c alone or inside a flag cluster such as
# -lc, -ic, or -xc. The settings prompt carries no text, so the reason below
# tells the agent what to do instead. Other interpreters are out of scope.
#
# A shell counts when it stands at a command position, as the splitting in
# lib/command_words.sh defines it, so `grep -c`, `echo "bash -c"`, and
# `bash script.sh -c` stay silent. The scan covers the shell's options only:
# it skips the value of -o, -O, +o, +O, --rcfile, and --init-file, and stops
# at -- or at the first word that is not an option.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when asking; nothing when staying silent.
# Exit:    0 in all cases (the decision travels on stdout, not the exit code).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"

readonly ASK_REASON="Run a shell with -c only to test how that shell behaves, or as zsh -ic '<command>' for a CLI whose credentials load only in an interactive shell. Otherwise write the step as a script file in the scratchpad and run that file."

#######################################
# Report whether a program line runs a shell with -c.
# Arguments:
#   The program's name, then its arguments.
# Returns:
#   0 when it is a shell run with -c, 1 otherwise.
#######################################
is_shell_c() {
  local program="$1" word skip=0
  shift

  case "${program}" in
  bash | sh | zsh | dash | ksh) ;;
  *) return 1 ;;
  esac

  for word in "$@"; do
    if ((skip)); then
      skip=0
      continue
    fi
    case "${word}" in
    -o | +o | -O | +O | --rcfile | --init-file)
      skip=1
      continue
      ;;
    --) return 1 ;;
    esac
    [[ "${word}" == -* || "${word}" == +* ]] || return 1
    if [[ "${word}" =~ ^-[A-Za-z]*c[A-Za-z]*$ ]]; then
      return 0
    fi
  done
  return 1
}

#######################################
# Emit an ask decision and exit.
# Outputs:
#   The permission decision JSON on stdout.
#######################################
ask() {
  jq -nc --arg r "${ASK_REASON}" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"ask",permissionDecisionReason:$r}}'
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
    if is_shell_c "${words[@]}"; then
      ask
    fi
  done < <(command_words::resolve "${command}")

  return 0
}

main "$@"
