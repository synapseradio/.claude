#!/bin/bash
#
# PreToolUse hook: deny sleep issued through Bash.
#
# A sleep holds the turn and the wall clock on a guess at how long something
# takes. A command run with run_in_background resumes the session when it
# exits, at no cost while it runs.

set -euo pipefail

# sleep at a command position: after the start of a line, a separator, an
# opening parenthesis, or a loop or branch keyword, optionally named by path.
# Anchoring keeps sleep inside a quoted argument or a longer word silent.
readonly SLEEP_PATTERN='(^|[|;&(]|&&)[[:space:]]*((do|then|else)[[:space:]]+)?([^[:space:]]*/)?sleep([[:space:];)]|$)'

readonly DENIAL_REASON='sleep is banned by the waiting-on-processes rule. Start a command that may take time with run_in_background set on the Bash call, do the work that does not depend on it, and end the turn: the harness resumes the session when the command exits. To wait on something outside the session, such as a CI run, run the command that blocks on it, such as gh run watch, in the background the same way. Never poll.'

main() {
  local input command
  input="$(cat)"
  command="$(jq -r '.tool_input.command // ""' <<<"${input}")"

  if [[ -z "${command}" ]]; then
    return 0
  fi

  if grep -Eq "${SLEEP_PATTERN}" <<<"${command}"; then
    jq -nc --arg reason "${DENIAL_REASON}" '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: $reason
      }
    }'
  fi

  return 0
}

main "$@"
