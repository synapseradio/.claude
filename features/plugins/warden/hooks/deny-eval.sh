#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Refuses (permissionDecision: "deny") a command that runs eval. eval parses
# a string a second time, so the text that runs is not the text anyone read.
#
# eval counts when it stands at a command position, as the splitting in
# lib/command_words.sh defines it: the start of the command, the start of any
# part after &&, ||, ;, |, a newline, or a subshell or $( opener, behind a
# wrapper such as sudo or env, and inside a `sh -c` string. The word eval as
# an argument, inside a quoted string, or as part of an option or a longer
# name stays allowed.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (the decision travels on stdout, not the exit code).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"

readonly DENIAL_REASON='eval parses its argument a second time, so the text that runs is not the text that was written. Write the step as a script file in the scratchpad and run that file, or run the command directly.'

#######################################
# Emit a deny decision and exit.
# Outputs:
#   The permission decision JSON on stdout.
#######################################
deny() {
  jq -nc --arg reason "${DENIAL_REASON}" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

main() {
  local command line
  command="$(jq -r '.tool_input.command // ""')"

  if [[ -z "${command}" ]]; then
    return 0
  fi

  while IFS= read -r line; do
    if [[ "${line}" == eval || "${line}" == eval\ * ]]; then
      deny
    fi
  done < <(command_words::resolve "${command}")

  return 0
}

main "$@"
