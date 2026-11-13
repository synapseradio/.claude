#!/usr/bin/env bats
#
# Tests for deny-eval.sh, the PreToolUse Bash guard that denies eval and
# points at a script file.
#
# The denial cases cover eval at each command position: alone, after each
# separator, in a subshell and a command substitution, behind wrapper words,
# inside a loop body, and in a shell -c string. The silent cases cover the
# word eval as an argument, an option, part of a longer name, inside a quoted
# string, in a comment, and in a here-document body.

# Single quotes are intentional throughout: the guard has to receive the
# literal text, never its expansion (SC2016). setup sets HOOK and the
# helpers read it, which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-eval.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  isolate_home
}

@test "a bare eval is denied" {
  assert_denies 'eval "$(ssh-agent -s)"'
}

@test "eval with a plain argument is denied" {
  assert_denies 'eval ls'
}

@test "eval after && is denied" {
  assert_denies 'cd build && eval "$CMD"'
}

@test "eval after || is denied" {
  assert_denies 'make || eval "$FALLBACK"'
}

@test "eval after a semicolon is denied" {
  assert_denies 'npm run build; eval "$CMD"'
}

@test "eval after a pipe is denied" {
  assert_denies 'echo x | eval'
}

@test "eval on a later line is denied" {
  assert_denies $'cd build\neval "$CMD"'
}

@test "eval inside a subshell is denied" {
  assert_denies '(cd build && eval "$CMD")'
}

@test "eval inside a command substitution is denied" {
  assert_denies 'echo $(eval "$CMD")'
}

@test "eval behind a variable assignment is denied" {
  assert_denies 'LC_ALL=C eval "$CMD"'
}

@test "eval inside a loop body is denied" {
  assert_denies 'for c in a b; do eval "$c"; done'
}

@test "eval after then is denied" {
  assert_denies 'if true; then eval "$CMD"; fi'
}

@test "eval in a bash -c string is denied" {
  assert_denies "bash -c 'echo start; eval \"\$CMD\"'"
}

@test "a quoted command word eval is denied" {
  assert_denies '"eval" ls'
}

@test "a denial points at a script file" {
  run_bash_hook 'eval ls'
  [[ "$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")" == *'script file in the scratchpad'* ]]
}

@test "git log --eval stays silent" {
  assert_silent 'git log --eval'
}

@test "eval as an argument to echo stays silent" {
  assert_silent 'echo eval'
}

@test "eval as an argument to grep stays silent" {
  assert_silent 'grep -n eval file.js'
}

@test "grep -c stays silent" {
  assert_silent 'grep -c eval file.js'
}

@test "eval inside a double-quoted string stays silent" {
  assert_silent 'echo "eval $CMD"'
}

@test "eval inside a single-quoted string stays silent" {
  assert_silent "echo 'run eval later'"
}

@test "eval in a commit message stays silent" {
  assert_silent 'git commit -m "fix: stop using eval"'
}

@test "a word starting with eval stays silent" {
  assert_silent 'evaluate --all'
}

@test "a file named eval stays silent" {
  assert_silent 'cat docs/eval.md'
}

@test "eval at the start of a here-document line stays silent" {
  assert_silent $'cat <<\'EOF\'\neval ls\nEOF'
}

@test "eval in a comment stays silent" {
  assert_silent $'ls # eval ls\npwd'
}

@test "an empty command stays silent" {
  assert_silent ''
}
