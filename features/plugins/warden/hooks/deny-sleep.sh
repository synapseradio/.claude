#!/bin/bash
#
# PreToolUse hook: deny sleep issued through Bash.
#
# A sleep holds the turn and the wall clock on a guess at how long something
# takes. A command run with run_in_background resumes the session when it
# exits, at no cost while it runs.
#
# sleep counts when it is a program the command runs, as the splitting in
# lib/command_words.sh defines it: at the start of the command or of any
# part after &&, ||, ;, |, &, a newline, or a subshell or $( opener, behind
# a wrapper such as nohup or env, named by path, and inside a `sh -c`
# string. The word sleep inside a quoted argument, a regex, a path, or a
# longer name names no program and stays allowed.
#
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

# What follows the quoted sleep command in the reason.
readonly DENIAL_STEM=' holds the session on a guess at how long something takes. Run the command in the background with run_in_background set on the Bash call, do the work that does not depend on it, and end the turn: the harness resumes the session with a completion notice when the command exits. To read a log or a result, run a command that exits, once. To wait on something outside the session, such as a CI run, run the command that blocks on it, such as gh run watch, in the background the same way.'

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

  if command_words::first_line sleep "${command}" line; then
    # The quoting helper is needed on a denial only.
    # shellcheck source=lib/reason_text.sh
    source "${SCRIPT_DIR}/lib/reason_text.sh"
    decision::reach deny "$(reason_text::quote "${line}" 40)${DENIAL_STEM}"
  fi
}

main() {
  decision::main_bash
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
