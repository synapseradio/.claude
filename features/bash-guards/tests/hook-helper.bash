# Shared helpers for the bash-guards hook tests.
#
# Every guard here reads one PreToolUse envelope on stdin and answers on
# stdout: a permission decision object when it objects, and nothing at all
# when it does not. The exit status stays 0 either way, so a guard that
# crashed and a guard that allowed look alike unless the status is checked
# too. These helpers check both.
#
# Each test file sets HOOK to the guard under test in its own setup, then
# loads this file. The guards run under `bash <path>`, which is how the
# harness invokes them.
#
# shellcheck shell=bash

# Set by run_bash_hook and run_read_hook, read by the assertions below.
HOOK_OUTPUT=''
HOOK_STATUS=0

# Point the banned-reads file at this test's own temporary directory. No
# case can then reach a file the machine already has, whatever the person
# running the tests keeps in their own Claude directory.
export BASH_GUARDS_BANNED_READS="${BATS_TEST_TMPDIR}/banned-reads.conf"

#######################################
# Feed one envelope to the guard under test.
# Globals:
#   HOOK, HOOK_OUTPUT, HOOK_STATUS
# Arguments:
#   $1 - the PreToolUse envelope JSON.
#######################################
run_hook_envelope() {
  local envelope="$1"
  HOOK_STATUS=0
  HOOK_OUTPUT="$(bash "${HOOK}" <<<"${envelope}")" || HOOK_STATUS=$?
}

#######################################
# Run the guard against a command the Bash tool proposes.
# Globals:
#   HOOK_OUTPUT, HOOK_STATUS
# Arguments:
#   $1 - the shell command.
#######################################
run_bash_hook() {
  local command="$1" envelope
  envelope="$(jq -nc --arg c "${command}" \
    '{tool_name:"Bash",tool_input:{command:$c}}')"
  run_hook_envelope "${envelope}"
}

#######################################
# Run the guard against a path the Read tool proposes to open.
# Globals:
#   HOOK_OUTPUT, HOOK_STATUS
# Arguments:
#   $1 - the file path.
#######################################
run_read_hook() {
  local path="$1" envelope
  envelope="$(jq -nc --arg p "${path}" \
    '{tool_name:"Read",tool_input:{file_path:$p}}')"
  run_hook_envelope "${envelope}"
}

#######################################
# Assert the guard exited 0, whatever it decided.
# Globals:
#   HOOK_STATUS, HOOK_OUTPUT
#######################################
assert_exited_clean() {
  ((HOOK_STATUS == 0)) || {
    echo "guard exited ${HOOK_STATUS}, wanted 0; output: ${HOOK_OUTPUT}" >&2
    return 1
  }
}

#######################################
# Assert the last run carried a given permission decision.
# Globals:
#   HOOK_OUTPUT
# Arguments:
#   $1 - the expected permissionDecision value.
#   $2 - the subject, quoted back on failure.
#######################################
assert_decision() {
  local want="$1" subject="$2" event decision
  assert_exited_clean || return 1
  [[ -n "${HOOK_OUTPUT}" ]] || {
    echo "expected a ${want}, got silence for: ${subject}" >&2
    return 1
  }
  event="$(jq -r '.hookSpecificOutput.hookEventName // ""' <<<"${HOOK_OUTPUT}")"
  [[ "${event}" == 'PreToolUse' ]] || {
    echo "expected hookEventName PreToolUse, got '${event}'" >&2
    return 1
  }
  decision="$(jq -r '.hookSpecificOutput.permissionDecision // ""' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${decision}" == "${want}" ]] || {
    echo "expected ${want}, got '${decision}' for: ${subject}" >&2
    return 1
  }
  [[ -n "$(jq -r '.hookSpecificOutput.permissionDecisionReason // ""' \
    <<<"${HOOK_OUTPUT}")" ]] || {
    echo "decision carried no reason for the user to read: ${subject}" >&2
    return 1
  }
}

#######################################
# Assert the guard said nothing about the last run.
# Globals:
#   HOOK_OUTPUT
# Arguments:
#   $1 - the subject, quoted back on failure.
#######################################
assert_no_decision() {
  local subject="$1"
  assert_exited_clean || return 1
  [[ -z "${HOOK_OUTPUT}" ]] || {
    echo "expected silence for: ${subject}; got: ${HOOK_OUTPUT}" >&2
    return 1
  }
}

#######################################
# Assert the guard denies a Bash command.
# Arguments:
#   $1 - the shell command.
#######################################
assert_denies() {
  run_bash_hook "$1"
  assert_decision 'deny' "$1"
}

#######################################
# Assert the guard asks about a Bash command.
# Arguments:
#   $1 - the shell command.
#######################################
assert_asks() {
  run_bash_hook "$1"
  assert_decision 'ask' "$1"
}

#######################################
# Assert the guard stays silent about a Bash command.
# Arguments:
#   $1 - the shell command.
#######################################
assert_silent() {
  run_bash_hook "$1"
  assert_no_decision "$1"
}

#######################################
# Assert the guard denies a Read target.
# Arguments:
#   $1 - the file path.
#######################################
assert_denies_read() {
  run_read_hook "$1"
  assert_decision 'deny' "$1"
}

#######################################
# Assert the guard stays silent about a Read target.
# Arguments:
#   $1 - the file path.
#######################################
assert_silent_read() {
  run_read_hook "$1"
  assert_no_decision "$1"
}
