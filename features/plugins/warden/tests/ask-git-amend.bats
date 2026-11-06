#!/usr/bin/env bats
#
# Tests for ask-git-amend.sh, the PreToolUse Bash hook that prompts when a
# command amends a commit.
#
# The ask cases cover --amend in each argument position, git with global
# options before the subcommand, and each command position. The silent cases
# cover other git subcommands, a commit without --amend, and --amend inside
# a message, a quoted string, or as an argument to another program.

setup() {
  export HOME="${BATS_TEST_TMPDIR}/home"
  export XDG_CONFIG_HOME="${HOME}/.config"
  export XDG_DATA_HOME="${HOME}/.local/share"
  export XDG_CACHE_HOME="${HOME}/.cache"
  export GIT_CONFIG_GLOBAL="${HOME}/gitconfig"
  export GIT_CONFIG_NOSYSTEM=1
  mkdir -p "${HOME}"
  HOOK="${BATS_TEST_DIRNAME}/../hooks/ask-git-amend.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
}

@test "git commit --amend asks" {
  assert_asks 'git commit --amend'
}

@test "git commit --amend --no-edit asks" {
  assert_asks 'git commit --amend --no-edit'
}

@test "git commit --amend with a message asks" {
  assert_asks 'git commit --amend -m "fix: wording"'
}

@test "git commit with --amend after a message asks" {
  assert_asks 'git commit -m "fix: wording" --amend'
}

@test "git commit with --amend after a combined flag asks" {
  assert_asks 'git commit -am "fix: wording" --amend'
}

@test "git commit with --amend between other flags asks" {
  assert_asks 'git commit -a --amend --no-verify'
}

@test "git -C path commit --amend asks" {
  assert_asks 'git -C /Users/me/repo commit --amend'
}

@test "git -c key=value commit --amend asks" {
  assert_asks 'git -c core.editor=true commit --amend'
}

@test "git --no-pager commit --amend asks" {
  assert_asks 'git --no-pager commit --amend'
}

@test "git --git-dir with a value commit --amend asks" {
  assert_asks 'git --git-dir /tmp/x/.git commit --amend'
}

@test "git named by path asks" {
  assert_asks '/usr/bin/git commit --amend'
}

@test "git commit --amend after && asks" {
  assert_asks 'git add -- a.txt && git commit --amend --no-edit'
}

@test "git commit --amend after a semicolon asks" {
  assert_asks 'git add -- a.txt; git commit --amend'
}

@test "git commit --amend on a later line asks" {
  assert_asks $'git add -- a.txt\ngit commit --amend'
}

@test "git commit --amend behind env asks" {
  assert_asks 'env GIT_EDITOR=true git commit --amend'
}

@test "git commit --amend in a subshell asks" {
  assert_asks '(git commit --amend --no-edit)'
}

@test "git commit --amend in a bash -c string asks" {
  assert_asks "bash -c 'git commit --amend'"
}

@test "an ask names committing anew" {
  run_bash_hook 'git commit --amend'
  [[ "$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")" == *'commit anew'* ]]
}

@test "a plain git commit stays silent" {
  assert_silent 'git commit -m "feat: add thing"'
}

@test "git -C path commit without --amend stays silent" {
  assert_silent 'git -C /Users/me/repo commit -m "feat: add thing"'
}

@test "git commit --fixup stays silent" {
  assert_silent 'git commit --fixup HEAD'
}

@test "git log stays silent" {
  assert_silent 'git log --oneline'
}

@test "git rebase stays silent" {
  assert_silent 'git rebase --autosquash origin/main'
}

@test "git status with --amend as a later word stays silent" {
  assert_silent 'git status --amend'
}

@test "--amend in a commit message stays silent" {
  assert_silent 'git commit -m "--amend"'
}

@test "--amend in a long-form message stays silent" {
  assert_silent 'git commit --message "--amend"'
}

@test "--amend named in a commit message sentence stays silent" {
  assert_silent 'git commit -m "docs: never git commit --amend"'
}

@test "--amend as an argument to echo stays silent" {
  assert_silent 'echo git commit --amend'
}

@test "--amend as an argument to grep stays silent" {
  assert_silent 'grep -rn -- "--amend" docs/'
}

@test "--amend inside a single-quoted string stays silent" {
  assert_silent "echo 'git commit --amend'"
}

@test "git commit --amend in a comment stays silent" {
  assert_silent $'ls # git commit --amend\npwd'
}

@test "git commit --amend in a here-document body stays silent" {
  assert_silent $'cat <<\'EOF\'\ngit commit --amend\nEOF'
}

@test "an empty command stays silent" {
  assert_silent ''
}
