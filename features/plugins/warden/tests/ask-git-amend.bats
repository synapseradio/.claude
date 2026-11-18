#!/usr/bin/env bats
#
# Tests for ask-git-amend.sh, the PreToolUse Bash hook that prompts when a
# command amends a commit.
#
# The ask cases cover --amend in each argument position, git with global
# options before the subcommand, and each command position. The silent cases
# cover other git subcommands, a commit without --amend, and --amend inside
# a message, a quoted string, or as an argument to another program.

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard ask-git-amend
  isolate_home
  export GIT_CONFIG_GLOBAL="${HOME}/gitconfig"
  export GIT_CONFIG_NOSYSTEM=1
}

@test "git commit asks when --amend sits at any flag position" {
  local -a forms=(
    'git commit --amend'
    'git commit --amend --no-edit'
    'git commit --amend -m "fix: wording"'
    'git commit -m "fix: wording" --amend'
    'git commit -am "fix: wording" --amend'
    'git commit -a --amend --no-verify'
  )
  local form
  for form in "${forms[@]}"; do
    assert_asks "${form}"
  done
}

@test "git commit --amend asks behind each global git option and a path-named git" {
  local -a forms=(
    'git -C /Users/me/repo commit --amend'
    'git -c core.editor=true commit --amend'
    'git --no-pager commit --amend'
    'git --git-dir /tmp/x/.git commit --amend'
    '/usr/bin/git commit --amend'
  )
  local form
  for form in "${forms[@]}"; do
    assert_asks "${form}"
  done
}

@test "git commit --amend asks at each command position" {
  local -a forms=(
    'git add -- a.txt && git commit --amend --no-edit'
    'git add -- a.txt; git commit --amend'
    $'git add -- a.txt\ngit commit --amend'
    'env GIT_EDITOR=true git commit --amend'
    '(git commit --amend --no-edit)'
    "bash -c 'git commit --amend'"
  )
  local form
  for form in "${forms[@]}"; do
    assert_asks "${form}"
  done
}

@test "git commands that do not amend stay silent" {
  local -a forms=(
    'git commit -m "feat: add thing"'
    'git -C /Users/me/repo commit -m "feat: add thing"'
    'git commit --fixup HEAD'
    'git log --oneline'
    'git rebase --autosquash origin/main'
    'git status --amend'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "--amend named as text, an argument, or an empty command stays silent" {
  local -a forms=(
    'git commit -m "--amend"'
    'git commit --message "--amend"'
    'git commit -m "docs: never git commit --amend"'
    'echo git commit --amend'
    'grep -rn -- "--amend" docs/'
    "echo 'git commit --amend'"
    $'ls # git commit --amend\npwd'
    $'cat <<\'EOF\'\ngit commit --amend\nEOF'
    ''
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "an envelope proposing git commit --amend prints a PreToolUse ask" {
  assert_main_prints ask \
    '{"tool_name":"Bash","tool_input":{"command":"git commit --amend --no-edit"}}'
}
