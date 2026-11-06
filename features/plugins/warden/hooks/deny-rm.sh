#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Refuses (permissionDecision: "deny") a command that runs rm. rm removes a
# file for good; trash moves it to the Trash, where it can be recovered.
#
# rm counts when it stands at a command position: the start of the command,
# or of any part after &&, ||, ;, |, a newline, or a subshell or $( opener,
# behind sudo, command, xargs, env, or exec, and inside a `sh -c` string or
# a find -exec. The splitting lives in lib/command_words.sh. `git rm`,
# `npm rm`, `docker rm`, rmdir, trash, and the word rm inside a quoted
# string or as an argument stay allowed.
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

readonly DENIAL_REASON='rm removes files for good. Delete with trash <path> instead: it moves the path to the Trash, where it can be recovered. Deleting still needs the confirmation the task calls for.'

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
    if [[ "${line}" == rm || "${line}" == rm\ * ]]; then
      deny
    fi
  done < <(command_words::resolve "${command}")

  return 0
}

main "$@"
