#!/usr/bin/env bats
#
# Tests for deny-unsafe-soft-reset.sh: the denials that turn on where the
# target sits in history, on the operand, and on the repository; a soft reset
# after another step or a directory change; git that fails or answers late;
# and the envelope main reads. Each case copies the scratch remote and clone
# the file builds. deny-unsafe-soft-reset.bats covers what passes and what
# the branch and repository state deny.

export BATS_TEST_TIMEOUT=10

setup_file() {
  export FIXTURE="${BATS_FILE_TMPDIR}/fixture"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load "${BATS_TEST_DIRNAME}/deny-unsafe-soft-reset-fixture.bash"
  export HOME="${BATS_FILE_TMPDIR}/home"
  mkdir -p "${HOME}"
  isolate_git_config
  build_fixture
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load "${BATS_TEST_DIRNAME}/deny-unsafe-soft-reset-fixture.bash"
  load_guard deny-unsafe-soft-reset
  isolate_home
  isolate_git_config
  copy_fixture
}

teardown() {
  release_hung_git
}

@test "a soft reset to a commit that is not an ancestor of HEAD is denied" {
  git -C "${WORK}" checkout -q -b elsewhere main
  commit_file elsewhere
  git -C "${WORK}" checkout -q feature
  assert_denies_in "${WORK}" 'git reset --soft elsewhere'
}

@test "a soft reset that rewinds a pushed commit is denied" {
  git -C "${WORK}" push -q origin feature
  assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "a soft reset past the pushed part of the branch is denied, short of it allowed" {
  git -C "${WORK}" push -q origin feature
  commit_file three
  assert_denies_in "${WORK}" 'git reset --soft HEAD~2'
  assert_silent_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "a soft reset of commits another remote-tracking ref holds is denied" {
  git -C "${WORK}" remote add backup "${REMOTE}"
  git -C "${WORK}" push -q backup feature
  git -C "${WORK}" fetch -q backup
  assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "an operand with a variable, glob, substitution, or reflog brace is denied" {
  local -a forms=(
    "git reset --soft \$PARENT"
    "git reset --soft \"\$PARENT\""
    'git reset --soft HEAD~*'
    "git reset --soft \$(git merge-base HEAD main)"
    "git reset --soft \`git merge-base HEAD main\`"
    'git reset --soft HEAD@{1}'
    'git reset --soft ~/HEAD'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies_in "${WORK}" "${form}"
  done
}

@test "a directory that is no repository is denied" {
  mkdir "${BATS_TEST_TMPDIR}/plain"
  assert_denies_in "${BATS_TEST_TMPDIR}/plain" 'git reset --soft HEAD~1'
}

@test "a -C path that cannot be judged, a global option that moves the repository, and a GIT_ variable are denied" {
  local -a forms=(
    "git -C ${BATS_TEST_TMPDIR}/missing reset --soft HEAD~1"
    "git -C \$REPO reset --soft HEAD~1"
    "git --git-dir=${WORK}/.git reset --soft HEAD~1"
    "git --work-tree=${WORK} reset --soft HEAD~1"
    'git -c core.x=y reset --soft HEAD~1'
    "GIT_DIR=${WORK}/.git git reset --soft HEAD~1"
    "env GIT_WORK_TREE=${WORK} git reset --soft HEAD~1"
    "env -C ${BATS_TEST_TMPDIR} git reset --soft HEAD~1"
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies_in "${WORK}" "${form}"
  done
}

@test "a soft reset with no working directory is denied" {
  assert_denies 'git reset --soft HEAD~1'
  assert_denies 'git -C work reset --soft HEAD~1'
  assert_denies_in '' 'git reset --soft HEAD~1'
  assert_silent "git -C ${WORK} reset --soft HEAD~2"
  assert_silent_in '' "git -C ${WORK} reset --soft HEAD~2"
}

@test "a soft reset that follows another step is denied" {
  local -a forms=(
    $'git status\ngit log --oneline\ngit reset --soft HEAD~1'
    'git status && git reset --soft HEAD~1'
    'git push; git reset --soft HEAD~1'
    'git reset --soft HEAD~1 && git reset --soft HEAD~1'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies_in "${WORK}" "${form}"
  done
}

@test "a soft reset by -C is judged against that path, not the envelope's cwd" {
  git -C "${WORK}" worktree add -q "${BATS_TEST_TMPDIR}/trunk" main
  git -C "${BATS_TEST_TMPDIR}/trunk" commit -q --allow-empty -m trunk-local
  assert_denies_in "${WORK}" "git -C ${BATS_TEST_TMPDIR}/trunk reset --soft HEAD~1"
  assert_silent_in "${BATS_TEST_TMPDIR}/trunk" "git -C ${WORK} reset --soft HEAD~2"
}

@test "git failing to run is denied" {
  local stubs="${BATS_TEST_TMPDIR}/stubs"
  mkdir -p "${stubs}"
  printf '#!/bin/bash\nexit 127\n' >"${stubs}/git"
  chmod +x "${stubs}/git"
  PATH="${stubs}:${PATH}" assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "git answering after the deadline is denied" {
  stub_hung_git
  WARDEN_SOFT_RESET_DEADLINE=1 assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "a soft reset after a directory change is denied" {
  assert_denies_in "${BATS_TEST_TMPDIR}" "cd ${WORK} && git reset --soft HEAD~1"
}

@test "an envelope proposing a soft reset past the first commit prints a PreToolUse denial" {
  assert_main_prints deny \
    "{\"tool_name\":\"Bash\",\"cwd\":\"${WORK}\",\"tool_input\":{\"command\":\"git reset --soft HEAD~3\"}}"
}
