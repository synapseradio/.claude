#!/usr/bin/env bats
#
# Tests for deny-unsafe-soft-reset.sh, the PreToolUse Bash guard that lets
# git reset --soft run only where it rewrites nothing but unpushed commits on
# a feature branch, and points everything else at wt step squash.
#
# The file builds a scratch bare remote and a clone of it once, and each case
# copies both under BATS_TEST_TMPDIR. The clone sits on a feature branch
# holding two commits no remote has. The first group covers what passes; the groups after it cover
# each condition that denies, the -C form, and the command positions the
# guard reads (after a separator, in a sh -c string, behind env).

# The single-quoted command texts below are the input under test, so their
# $ and backticks must stay literal (SC2016). bats reads BATS_TEST_TIMEOUT,
# which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

BATS_TEST_TIMEOUT=10

setup_file() {
  export FIXTURE="${BATS_FILE_TMPDIR}/fixture"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  export HOME="${BATS_FILE_TMPDIR}/home"
  mkdir -p "${HOME}"
  isolate_git_config
  build_fixture
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard deny-unsafe-soft-reset
  isolate_home
  isolate_git_config
  copy_fixture
}

#######################################
# Commit one file in the work clone.
# Globals:
#   WORK
# Arguments:
#   $1 - the file name, also its content.
#######################################
commit_file() {
  printf '%s\n' "$1" >"${WORK}/$1"
  git -C "${WORK}" add -- "$1"
  git -C "${WORK}" commit -q -m "add $1"
}

#######################################
# Build, once for the file, a bare remote holding main, a clone of it, and a
# feature branch with two commits that no remote has.
# Globals:
#   FIXTURE, WORK
#######################################
build_fixture() {
  local seed="${FIXTURE}/seed" remote="${FIXTURE}/remote.git"
  WORK="${FIXTURE}/work"
  git init -q --bare -b main "${remote}"
  git init -q -b main "${seed}"
  printf 'base\n' >"${seed}/base.txt"
  git -C "${seed}" add -A
  git -C "${seed}" commit -q -m seed
  git -C "${seed}" remote add origin "${remote}"
  git -C "${seed}" push -q origin main
  git clone -q "${remote}" "${WORK}"
  git -C "${WORK}" checkout -q -b feature
  commit_file one
  commit_file two
}

#######################################
# Give this case its own copy of the fixture's remote and clone, the clone
# pointed at the copied remote. A case may push, add a remote, or move
# origin/HEAD without touching another case.
# Globals:
#   FIXTURE, REMOTE, WORK, BATS_TEST_TMPDIR
#######################################
copy_fixture() {
  REMOTE="${BATS_TEST_TMPDIR}/remote.git"
  WORK="${BATS_TEST_TMPDIR}/work"
  cp -R "${FIXTURE}/remote.git" "${REMOTE}"
  cp -R "${FIXTURE}/work" "${WORK}"
  git -C "${WORK}" remote set-url origin "${REMOTE}"
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
    'git reset --soft $PARENT'
    'git reset --soft "$PARENT"'
    'git reset --soft HEAD~*'
    'git reset --soft $(git merge-base HEAD main)'
    'git reset --soft `git merge-base HEAD main`'
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
    'git -C $REPO reset --soft HEAD~1'
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
  local stubs="${BATS_TEST_TMPDIR}/stubs"
  mkdir -p "${stubs}"
  printf '#!/bin/bash\nexec sleep 10\n' >"${stubs}/git"
  chmod +x "${stubs}/git"
  PATH="${stubs}:${PATH}" WARDEN_SOFT_RESET_DEADLINE=1 \
    assert_denies_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "a soft reset after a directory change is denied" {
  assert_denies_in "${BATS_TEST_TMPDIR}" "cd ${WORK} && git reset --soft HEAD~1"
}

@test "an envelope proposing a soft reset past the first commit prints a PreToolUse denial" {
  assert_main_prints deny \
    "{\"tool_name\":\"Bash\",\"cwd\":\"${WORK}\",\"tool_input\":{\"command\":\"git reset --soft HEAD~3\"}}"
}
