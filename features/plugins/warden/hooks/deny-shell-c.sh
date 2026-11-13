#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Refuses (permissionDecision: "deny") a command that runs a shell with -c:
# bash, sh, zsh, dash, or ksh, with -c alone or inside a flag cluster such as
# -lc or -xc. A -c string is text that runs without standing as a command of
# its own. zsh with both -i and -c prompts (permissionDecision: "ask") in
# place of a refusal: a CLI whose credentials load only in an interactive
# shell has no other way to run. Other interpreters are out of scope.
#
# A shell counts when it stands at a command position, as the splitting in
# lib/command_words.sh defines it, so `grep -c`, `echo "bash -c"`, and
# `bash script.sh -c` stay silent. The scan covers the shell's options only:
# it skips the value of -o, -O, +o, +O, --rcfile, and --init-file, and stops
# at -- or at the first word that is not an option.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying or asking; nothing otherwise.
# Exit:    0 in all cases (the decision travels on stdout, not the exit code).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"

readonly DENIAL_REASON="A shell run with -c executes a string that never stands as a command of its own. Write the step as a script file in the scratchpad and run that file, with the shell under test where the point is how that shell behaves (zsh <file>, /bin/bash <file>). A CLI whose credentials load only in an interactive shell runs as zsh -ic '<command>', which prompts."
readonly ASK_REASON="zsh -ic runs a string in an interactive shell, which a CLI whose credentials load only there needs. Approve only that use."

# What shell_c_decision decided about the last program line: "deny", "ask", or
# empty.
SHELL_C_DECISION=''

#######################################
# Classify a program line's use of a shell with -c.
# Globals:
#   SHELL_C_DECISION
# Arguments:
#   The program's name, then its arguments.
# Outputs:
#   Nothing; SHELL_C_DECISION is "deny" for a shell run with -c, "ask" for
#   zsh run with -i and -c, empty otherwise.
#######################################
shell_c_decision() {
  local program="$1" word skip=0 interactive=0 runs_string=0
  shift
  SHELL_C_DECISION=''

  case "${program}" in
  bash | sh | zsh | dash | ksh) ;;
  *) return 0 ;;
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
    --) break ;;
    esac
    [[ "${word}" == -* || "${word}" == +* ]] || break
    [[ "${word}" =~ ^-[A-Za-z]*i[A-Za-z]*$ ]] && interactive=1
    [[ "${word}" =~ ^-[A-Za-z]*c[A-Za-z]*$ ]] && runs_string=1
  done

  ((runs_string)) || return 0
  if [[ "${program}" == zsh ]] && ((interactive)); then
    SHELL_C_DECISION=ask
  else
    SHELL_C_DECISION=deny
  fi
}

#######################################
# Emit a permission decision and exit.
# Arguments:
#   $1 - "deny" or "ask".
# Outputs:
#   The permission decision JSON on stdout.
#######################################
decide() {
  local decision="$1" reason="${DENIAL_REASON}"
  [[ "${decision}" == ask ]] && reason="${ASK_REASON}"
  jq -nc --arg d "${decision}" --arg r "${reason}" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:$d,permissionDecisionReason:$r}}'
  exit 0
}

main() {
  local command line asked=0
  local -a words
  command="$(jq -r '.tool_input.command // ""')"

  if [[ -z "${command}" ]]; then
    return 0
  fi

  while IFS= read -r line; do
    IFS=' ' read -r -a words <<<"${line}"
    shell_c_decision "${words[@]}"
    [[ "${SHELL_C_DECISION}" == deny ]] && decide deny
    [[ "${SHELL_C_DECISION}" == ask ]] && asked=1
  done < <(command_words::resolve "${command}")

  if ((asked)); then
    decide ask
  fi
  return 0
}

main "$@"
