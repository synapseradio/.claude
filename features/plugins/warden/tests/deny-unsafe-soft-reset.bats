#!/usr/bin/env bats
#
# Tests for deny-unsafe-soft-reset.sh, the PreToolUse Bash guard that lets
# git reset --soft run only where it rewrites nothing but unpushed commits on
# a feature branch, and points everything else at wt step squash.
#
# The file builds a scratch bare remote and a clone of it once, and each case
# copies both under BATS_TEST_TMPDIR. The clone sits on a feature branch
# holding two commits no remote has. The first group covers what passes, at
# each command position the guard reads and by -C; the groups after it cover
# the revision forms, mode flags, in-progress operations, detached HEAD, and
# default branches that deny. deny-unsafe-soft-reset-target.bats covers where
# the target sits in history, the operand, the repository, git failing, and
# the envelope.

# The single-quoted command texts below are the input under test, so their
# $ and backticks must stay literal (SC2016). bats reads BATS_TEST_TIMEOUT,
# which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

BATS_TEST_TIMEOUT=10

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

@test "a soft reset of unpushed feature-branch commits is allowed in each spelling and at each command position" {
  local -a forms=(
    'git reset --soft HEAD~2'
    'git reset --soft HEAD~1'
    "git reset --soft $(git -C "${WORK}" rev-parse HEAD~1)"
    'git reset --soft origin/main'
    'git reset -q --soft HEAD'
    'git reset --soft origin/main && git commit -m squashed'
    "sh -c 'git reset --soft HEAD~2'"
    'env FOO=1 git reset --soft HEAD~2'
    $'git reset --soft HEAD~2\ngit commit -m squashed\ngit log --oneline'
    'git reset --soft HEAD~1; echo done'
    'git reset --so HEAD~1'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent_in "${WORK}" "${form}"
  done
}

@test "a soft reset by -C is allowed from another directory" {
  local -a forms=(
    "git -C ${WORK} reset --soft HEAD~2"
    'git -C work reset --soft HEAD~2'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent_in "${BATS_TEST_TMPDIR}" "${form}"
  done
}

@test "a soft reset in a linked worktree is allowed" {
  git -C "${WORK}" worktree add -q -b wt-feature "${BATS_TEST_TMPDIR}/linked" main
  git -C "${BATS_TEST_TMPDIR}/linked" commit -q --allow-empty -m wt-one
  assert_silent_in "${BATS_TEST_TMPDIR}/linked" 'git reset --soft HEAD~1'
}

@test "the guard ignores a GIT_DIR inherited from the caller" {
  GIT_DIR="${BATS_TEST_TMPDIR}/nowhere/.git" \
    assert_silent_in "${WORK}" 'git reset --soft HEAD~2'
}

@test "commands that are not a soft reset stay silent" {
  local -a forms=(
    'git status'
    'git reset HEAD~1'
    'git reset --mixed HEAD~1'
    'git commit -m "git reset --soft HEAD~2"'
    'echo "git reset --soft HEAD~2"'
    'grep -n reset --soft file'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent_in "${WORK}" "${form}"
  done
}

@test "a soft reset naming anything but one resolvable revision is denied" {
  local -a forms=(
    'git reset --soft'
    'git reset --soft HEAD~1 HEAD~2'
    'git reset --soft HEAD~1 -- one'
    'git reset --soft -- one'
    'git reset --soft -p HEAD~1'
    'git reset --soft --recurse-submodules HEAD~1'
    'git reset --soft no-such-ref'
    'git reset --so --hard HEAD~1'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies_in "${WORK}" "${form}"
  done
}

@test "a soft reset beside a second mode flag is denied" {
  local flag
  for flag in --hard --mixed --merge --keep; do
    assert_denies_in "${WORK}" "git reset --soft ${flag} HEAD~1"
    assert_denies_in "${WORK}" "git reset ${flag} --soft HEAD~1"
    assert_denies_in "${WORK}" "git reset --soft HEAD~1 ${flag}"
  done
}

@test "a soft reset during a rebase, merge, cherry-pick, or revert is denied" {
  local marker git_dir
  git_dir="${WORK}/.git"
  for marker in rebase-merge rebase-apply sequencer; do
    mkdir "${git_dir}/${marker}"
    assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
    rmdir "${git_dir}/${marker}"
  done
  for marker in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD; do
    git -C "${WORK}" rev-parse HEAD >"${git_dir}/${marker}"
    assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
    rm -f "${git_dir}/${marker}"
  done
  assert_silent_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "a soft reset on a detached HEAD is denied" {
  git -C "${WORK}" checkout -q --detach
  assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "a soft reset on the default branch is denied, however the command reaches git" {
  git -C "${WORK}" checkout -q main
  commit_file local-only
  assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
  assert_denies_in "${WORK}" "sh -c 'git reset --soft HEAD~1'"
  assert_denies_in "${WORK}" 'env FOO=1 git reset --soft HEAD~1'
  assert_denies_in "${BATS_TEST_TMPDIR}" "git -C ${WORK} reset --soft HEAD~1"
}

@test "a soft reset on the branch origin/HEAD names is denied when it is not main" {
  git -C "${WORK}" push -q origin main:trunk
  git -C "${WORK}" fetch -q origin
  git -C "${WORK}" remote set-head origin trunk
  git -C "${WORK}" checkout -q -b trunk origin/trunk
  commit_file trunk-local
  assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
  git -C "${WORK}" checkout -q feature
  assert_silent_in "${WORK}" 'git reset --soft HEAD~2'
}

@test "main and master count as default when origin/HEAD is not set" {
  git -C "${WORK}" remote set-head origin --delete
  git -C "${WORK}" checkout -q main
  commit_file local-only
  assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
  git -C "${WORK}" checkout -q -b master
  assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
  git -C "${WORK}" checkout -q feature
  assert_silent_in "${WORK}" 'git reset --soft HEAD~2'
}
