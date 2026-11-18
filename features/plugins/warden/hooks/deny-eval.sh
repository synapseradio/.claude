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
# shellcheck source=lib/reason_text.sh
source "${SCRIPT_DIR}/lib/reason_text.sh"

readonly DENIAL_REASON='eval parses its argument a second time, so the text that runs is not the text that was written. Write the step as a script file in the scratchpad and run that file, or run the command directly.'

# The reason eval_reason composed.
EVAL_REASON=''

#######################################
# Compose the reason for a denied eval, scoped to its argument where the
# argument is literal text: that text is the command to run in eval's place.
# Where the argument is built at run time (a variable or a substitution), the
# reason says to print the text, read it, and run that.
# Globals:
#   EVAL_REASON
# Arguments:
#   $1 - the whole command text.
#   $2 - the eval program line, as the resolver prints it.
#######################################
eval_reason() {
  local command="$1" line="$2" text span
  EVAL_REASON="${DENIAL_REASON}"
  text="${line#eval}"
  text="$(reason_text::restore "${text# }")"
  span="$(reason_text::span "${text}" 100)"

  if [[ "${command}" == *"\$("* || "${command}" == *'`'* ]]; then
    EVAL_REASON="${DENIAL_REASON} The text eval runs comes from a substitution that runs first: run that inner command on its own, read what it prints, then run that text directly."
  elif [[ "${text}" == *'$'* ]]; then
    EVAL_REASON="${DENIAL_REASON} The text eval runs is built at run time (eval ${span}): print it with echo, read it, then run that command directly."
  elif [[ -n "${text// /}" ]]; then
    EVAL_REASON="${DENIAL_REASON} Here the argument is literal, so drop eval and run it directly: ${span}"
    if ((${#text} > 100)); then
      EVAL_REASON+=" (shortened here)."
    fi
  fi
  return 0
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

  if line="$(command_words::first_line eval "${command}")"; then
    eval_reason "${command}" "${line}"
    decision::reach deny "${EVAL_REASON}"
  fi
}

main() {
  decision::main_bash
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
