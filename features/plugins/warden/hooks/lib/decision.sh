#!/bin/bash
#
# Library for the warden guards: the decision a guard reaches about one tool
# call, and the JSON that carries it to the harness. Source it; it defines
# functions and the globals below only. Uses only what /bin/bash 3.2 on macOS
# offers.
#
# A guard's decision function fills the globals and prints nothing; its main
# reads the envelope, calls that function, and prints through
# decision::print, so a test can call the decision function in its own shell.
#
# Globals: GUARD_DECISION, GUARD_REASON.

# The globals are this library's results; the guards that source it set them.
# shellcheck disable=SC2034

# The decision on the last tool call judged: "deny", "ask", or empty where the
# guard has nothing to say, and the reason shown with it.
GUARD_DECISION=''
GUARD_REASON=''

#######################################
# Forget the last decision, ahead of judging a new tool call.
# Globals:
#   GUARD_DECISION, GUARD_REASON
#######################################
decision::clear() {
  GUARD_DECISION=''
  GUARD_REASON=''
}

#######################################
# Record a decision.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - "deny" or "ask".
#   $2 - the reason shown with it.
#######################################
decision::reach() {
  GUARD_DECISION="$1"
  GUARD_REASON="$2"
}

#######################################
# Print the recorded decision as the PreToolUse hook output, or nothing when
# there is none.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Outputs:
#   The permission decision JSON on stdout.
#######################################
decision::print() {
  [[ -n "${GUARD_DECISION}" ]] || return 0
  jq -nc --arg d "${GUARD_DECISION}" --arg r "${GUARD_REASON}" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:$d,permissionDecisionReason:$r}}'
}

#######################################
# Say whether a decision is recorded.
# Globals:
#   GUARD_DECISION
# Returns:
#   0 when one is, 1 otherwise.
#######################################
decision::reached() {
  [[ -n "${GUARD_DECISION}" ]]
}

#######################################
# Read a Bash tool envelope on stdin, judge its command with the guard's
# decide_bash, and print the decision. The body of a Bash guard's main.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Outputs:
#   The permission decision JSON on stdout, or nothing.
#######################################
decision::main_bash() {
  local command
  command="$(jq -r '.tool_input.command // ""')"
  decide_bash "${command}"
  decision::print
}
