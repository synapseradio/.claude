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

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"

readonly DENIAL_REASON='sleep holds the session on a guess at how long something takes. Run the command in the background with run_in_background set on the Bash call, do the work that does not depend on it, and end the turn: the harness resumes the session with a completion notice when the command exits. To read a log or a result, run a command that exits, once. To wait on something outside the session, such as a CI run, run the command that blocks on it, such as gh run watch, in the background the same way.'

main() {
  local input command line
  input="$(cat)"
  command="$(jq -r '.tool_input.command // ""' <<<"${input}")"

  if [[ -z "${command}" ]]; then
    return 0
  fi

  while IFS= read -r line; do
    if [[ "${line}" == sleep || "${line}" == sleep\ * ]]; then
      jq -nc --arg reason "${DENIAL_REASON}" '{
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: $reason
        }
      }'
      return 0
    fi
  done < <(command_words::resolve "${command}")

  return 0
}

main "$@"
