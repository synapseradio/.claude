#!/usr/bin/env bats
#
# Tests for deny-sleep.sh, the PreToolUse Bash guard that denies sleep.
#
# The denial cases cover sleep at each command position: alone, after a
# separator, inside a loop body, and named by path. The silent cases cover a
# word that only contains sleep and a mention inside a quoted argument.

# Single quotes are intentional throughout: the guard has to receive the
# literal text, never its expansion (SC2016).
# shellcheck disable=SC2016

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard deny-sleep
  isolate_home
}

@test "sleep is denied at each command position and behind each wrapper" {
  local -a forms=(
    'sleep 5'
    'sleep 30 && gh run view 123'
    'npm run build; sleep 2'
    'until curl -sf localhost:3000; do sleep 1; done'
    'if true; then sleep 1; fi'
    $'npm start &\nsleep 3'
    '/bin/sleep 1'
    '(sleep 1)'
    'make && sleep 5'
    'echo "$(sleep 5)"'
    'nohup sleep 5 &'
    "bash -c 'sleep 5'"
    'FOO=1 sleep 5'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "sleep named as text, inside a path, or as part of a longer word stays silent" {
  local -a forms=(
    'grep -rn sleepy src/'
    "grep -rn 'sleep 5' scripts/"
    'cat docs/sleep-timing.md'
    ''
    "rg -n '(git|sleep)[ ]' /x"
    "grep -E 'make;sleep|wait' scripts/"
    'rg -n "&& sleep 5" scripts/'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "an envelope proposing sleep prints a PreToolUse denial" {
  assert_main_prints deny '{"tool_name":"Bash","tool_input":{"command":"sleep 5"}}'
}
