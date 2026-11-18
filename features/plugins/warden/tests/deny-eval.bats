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
# literal text, never its expansion (SC2016).
# shellcheck disable=SC2016

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard deny-eval
  isolate_home
}

@test "eval is denied at each command position and behind a quoted command word" {
  local -a forms=(
    'eval "$(ssh-agent -s)"'
    'eval ls'
    'cd build && eval "$CMD"'
    'make || eval "$FALLBACK"'
    'npm run build; eval "$CMD"'
    'echo x | eval'
    $'cd build\neval "$CMD"'
    '(cd build && eval "$CMD")'
    'echo $(eval "$CMD")'
    'LC_ALL=C eval "$CMD"'
    'for c in a b; do eval "$c"; done'
    'if true; then eval "$CMD"; fi'
    "bash -c 'echo start; eval \"\$CMD\"'"
    '"eval" ls'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "eval named as an argument, inside text, or as part of a longer word stays silent" {
  local -a forms=(
    'git log --eval'
    'echo eval'
    'grep -n eval file.js'
    'grep -c eval file.js'
    'echo "eval $CMD"'
    "echo 'run eval later'"
    'git commit -m "fix: stop using eval"'
    'evaluate --all'
    'cat docs/eval.md'
    $'cat <<\'EOF\'\neval ls\nEOF'
    $'ls # eval ls\npwd'
    ''
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "an envelope proposing eval prints a PreToolUse denial" {
  assert_main_prints deny \
    '{"tool_name":"Bash","tool_input":{"command":"eval ls"}}'
}
