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
# Compose the reason for a denied eval, scoped to its argument where the
# argument is literal text: that text is the command to run in eval's place.
# Where the argument is built at run time (a variable or a substitution), the
# reason says to print the text, read it, and run that.
# Globals:
#   DENIAL_REASON, CW_SPACE
# Arguments:
#   $1 - the whole command text.
#   $2 - the eval program line, as the resolver prints it.
# Outputs:
#   The reason on stdout.
#######################################
eval_reason() {
  local command="$1" line="$2" text
  text="${line#eval}"
  text="${text# }"

  if [[ "${command}" == *"\$("* || "${command}" == *'`'* ]]; then
    printf '%s\n' "${DENIAL_REASON} The text eval runs comes from a substitution that runs first: run that inner command on its own, read what it prints, then run that text directly."
  elif [[ "${text}" == *'$'* ]]; then
    printf '%s\n' "${DENIAL_REASON} The text eval runs is built at run time (eval $(reason_text::quote "${text}" 100)): print it with echo, read it, then run that command directly."
  elif [[ -n "${text//[ ${CW_SPACE}]/}" ]]; then
    printf '%s\n' "${DENIAL_REASON} Here the argument is literal, so drop eval and run it directly: $(reason_text::quote "${text}" 100 ' (shortened here).')"
  else
    printf '%s\n' "${DENIAL_REASON}"
  fi
}

#######################################
# Decide on a command the Bash tool proposes.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the command.
#######################################
decide_bash() {
  local command="$1" line
  decision::clear

  if [[ -z "${command}" ]]; then
    return 0
  fi

  if command_words::first_line eval "${command}" line; then
    # The quoting helper is needed on a denial only.
    # shellcheck source=lib/reason_text.sh
    source "${SCRIPT_DIR}/lib/reason_text.sh"
    decision::reach deny "$(eval_reason "${command}" "${line}")"
  fi
}

main() {
  decision::main_bash
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
