#!/usr/bin/env bats
#
# Tests for deny-sleep.sh, the PreToolUse Bash guard that denies sleep.
#
# The denial cases cover sleep at each command position: alone, after a
# separator, inside a loop body, and named by path. The silent cases cover a
# word that only contains sleep and a mention inside a quoted argument.

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-sleep.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
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
