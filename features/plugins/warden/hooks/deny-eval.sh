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
# Sourced: defines decide_bash and main, and runs neither.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -euo pipefail
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"
# shellcheck source=lib/decision.sh
source "${SCRIPT_DIR}/lib/decision.sh"

readonly DENIAL_REASON='eval parses its argument a second time, so the text that runs is not the text that was written. Write the step as a script file in the scratchpad and run that file, or run the command directly.'

#######################################
# Decide on a command the Bash tool proposes.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the command.
#######################################
decide_bash() {
  local command="$1"
  decision::clear

  if [[ -z "${command}" ]]; then
    return 0
  fi

  if command_words::runs eval "${command}"; then
    decision::reach deny "${DENIAL_REASON}"
  fi
}

main() {
  decision::main_bash
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
