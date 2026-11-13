#!/usr/bin/env bats
#
# Tests for deny-sleep.sh, the PreToolUse Bash guard that denies sleep.
#
# The denial cases cover sleep at each command position: alone, after a
# separator, inside a loop body, and named by path. The silent cases cover a
# word that only contains sleep and a mention inside a quoted argument.

# Single quotes are intentional throughout: the guard has to receive the
# literal text, never its expansion (SC2016). setup sets HOOK and the
# helpers read it, which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-sleep.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  isolate_home
}

@test "a bare sleep is denied" {
  assert_denies 'sleep 5'
}

@test "sleep chained with && is denied" {
  assert_denies 'sleep 30 && gh run view 123'
}

@test "sleep after a semicolon is denied" {
  assert_denies 'npm run build; sleep 2'
}

@test "sleep inside a loop body is denied" {
  assert_denies 'until curl -sf localhost:3000; do sleep 1; done'
}

@test "sleep after then is denied" {
  assert_denies 'if true; then sleep 1; fi'
}

@test "sleep on its own line is denied" {
  assert_denies $'npm start &\nsleep 3'
}

@test "sleep named by path is denied" {
  assert_denies '/bin/sleep 1'
}

@test "sleep inside a subshell is denied" {
  assert_denies '(sleep 1)'
}

@test "a denial points at run_in_background" {
  run_bash_hook 'sleep 5'
  [[ "$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")" == *'run_in_background'* ]]
}

@test "a denial states the replacement act and cites no rule" {
  run_bash_hook 'sleep 5'
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'completion notice'* ]]
  [[ "${reason}" == *'a command that exits, once'* ]]
  [[ "${reason}" != *'waiting-on-processes'* ]]
}

@test "a word containing sleep stays silent" {
  assert_silent 'grep -rn sleepy src/'
}

@test "sleep named inside a quoted argument stays silent" {
  assert_silent "grep -rn 'sleep 5' scripts/"
}

@test "sleep named inside a path stays silent" {
  assert_silent 'cat docs/sleep-timing.md'
}

@test "an empty command stays silent" {
  assert_silent ''
}

@test "sleep named inside a quoted regex stays silent" {
  assert_silent "rg -n '(git|sleep)[ ]' /x"
  assert_silent "grep -E 'make;sleep|wait' scripts/"
  assert_silent 'rg -n "&& sleep 5" scripts/'
}

@test "sleep after && and inside a substitution is denied" {
  assert_denies 'make && sleep 5'
  assert_denies 'echo "$(sleep 5)"'
}

@test "sleep behind a wrapper or in a shell string is denied" {
  assert_denies 'nohup sleep 5 &'
  assert_denies "bash -c 'sleep 5'"
  assert_denies 'FOO=1 sleep 5'
}
