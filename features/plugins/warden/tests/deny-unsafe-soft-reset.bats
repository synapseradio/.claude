#!/usr/bin/env bats
#
# Tests for deny-unsafe-soft-reset.sh, the PreToolUse Bash guard that lets
# git reset --soft run only where it rewrites nothing but unpushed commits on
# a feature branch, and points everything else at wt step squash.
#
# Every case builds a scratch bare remote and a clone of it under
# BATS_TEST_TMPDIR. The clone sits on a feature branch holding two commits no
# remote has. The first group covers what passes; the groups after it cover
# each condition that denies, the -C form, and the command positions the
# guard reads (after a separator, in a sh -c string, behind env).

# The single-quoted command texts below are the input under test, so their
# $ and backticks must stay literal (SC2016). bats reads BATS_TEST_TIMEOUT
# and the helpers read HOOK, which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

BATS_TEST_TIMEOUT=10

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-unsafe-soft-reset.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  isolate_home
  export GIT_CONFIG_GLOBAL="${HOME}/.gitconfig"
  export GIT_CONFIG_NOSYSTEM=1
  printf '[user]\n\tname = Test\n\temail = test@example.com\n' \
    >"${GIT_CONFIG_GLOBAL}"
  # A hook run from a linked worktree inherits these, and a scratch
  # repository that kept them would write into the repository that holds
  # the tests.
  unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_COMMON_DIR \
    GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_NAMESPACE \
    GIT_CEILING_DIRECTORIES
  make_repo
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
# Build a bare remote holding main, a clone of it, and a feature branch with
# two commits that no remote has.
# Globals:
#   REMOTE, WORK, BATS_TEST_TMPDIR
#######################################
make_repo() {
  local seed="${BATS_TEST_TMPDIR}/seed"
  REMOTE="${BATS_TEST_TMPDIR}/remote.git"
  WORK="${BATS_TEST_TMPDIR}/work"
  git init -q --bare -b main "${REMOTE}"
  git init -q -b main "${seed}"
  printf 'base\n' >"${seed}/base.txt"
  git -C "${seed}" add -A
  git -C "${seed}" commit -q -m seed
  git -C "${seed}" remote add origin "${REMOTE}"
  git -C "${seed}" push -q origin main
  git clone -q "${REMOTE}" "${WORK}"
  git -C "${WORK}" checkout -q -b feature
  commit_file one
  commit_file two
}

#######################################
# Assert the last denial's reason contains a string.
# Globals:
#   HOOK_OUTPUT
# Arguments:
#   $1 - the text the reason must hold.
#######################################
assert_reason_contains() {
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *"$1"* ]] || {
    echo "reason lacks '$1': ${reason}" >&2
    return 1
  }
}

#######################################
# Assert the guard denies a command run from the work clone, with a reason
# that names the failed condition and points at wt step squash.
# Arguments:
#   $1 - the shell command.
#   $2 - text the reason must hold.
#######################################
assert_denied_because() {
  assert_denies_in "${WORK}" "$1"
  assert_reason_contains "$2"
  assert_reason_contains 'wt -C <worktree> step squash <target>'
}

@test "a soft reset of unpushed feature-branch commits is allowed" {
  assert_silent_in "${WORK}" 'git reset --soft HEAD~2'
  assert_silent_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "a soft reset to a revision spelled as a hash or origin/main is allowed" {
  assert_silent_in "${WORK}" "git reset --soft $(git -C "${WORK}" rev-parse HEAD~1)"
  assert_silent_in "${WORK}" 'git reset --soft origin/main'
}

@test "a soft reset to HEAD with --quiet is allowed" {
  assert_silent_in "${WORK}" 'git reset -q --soft HEAD'
}

@test "a soft reset by abbreviated flag is judged as a soft reset" {
  assert_silent_in "${WORK}" 'git reset --so HEAD~1'
  assert_denied_because 'git reset --so --hard HEAD~1' 'second mode flag'
}

@test "a commit after the soft reset is allowed" {
  assert_silent_in "${WORK}" 'git reset --soft origin/main && git commit -m squashed'
}

@test "the -C form is allowed with an absolute path from another directory" {
  assert_silent_in "${BATS_TEST_TMPDIR}" "git -C ${WORK} reset --soft HEAD~2"
}

@test "the -C form is allowed with a relative path against the envelope cwd" {
  assert_silent_in "${BATS_TEST_TMPDIR}" 'git -C work reset --soft HEAD~2'
}

@test "a soft reset in a sh -c string is allowed" {
  assert_silent_in "${WORK}" "sh -c 'git reset --soft HEAD~2'"
}

@test "a soft reset behind env is allowed" {
  assert_silent_in "${WORK}" 'env FOO=1 git reset --soft HEAD~2'
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
  assert_silent_in "${WORK}" 'git status'
  assert_silent_in "${WORK}" 'git reset HEAD~1'
  assert_silent_in "${WORK}" 'git reset --mixed HEAD~1'
  assert_silent_in "${WORK}" 'git commit -m "git reset --soft HEAD~2"'
  assert_silent_in "${WORK}" 'echo "git reset --soft HEAD~2"'
  assert_silent_in "${WORK}" 'grep -n reset --soft file'
}

@test "a soft reset naming no revision is denied" {
  assert_denied_because 'git reset --soft' 'exactly one revision'
}

@test "a soft reset naming two operands is denied" {
  assert_denied_because 'git reset --soft HEAD~1 HEAD~2' 'exactly one revision'
}

@test "a soft reset with a pathspec is denied" {
  assert_denied_because 'git reset --soft HEAD~1 -- one' 'pathspec'
  assert_denied_because 'git reset --soft -- one' 'pathspec'
}

@test "a soft reset beside a second mode flag is denied" {
  local flag
  for flag in --hard --mixed --merge --keep; do
    assert_denied_because "git reset --soft ${flag} HEAD~1" 'second mode flag'
    assert_denied_because "git reset ${flag} --soft HEAD~1" 'second mode flag'
    assert_denied_because "git reset --soft HEAD~1 ${flag}" 'second mode flag'
  done
}

@test "a soft reset with another option is denied" {
  assert_denied_because 'git reset --soft -p HEAD~1' 'option'
  assert_denied_because 'git reset --soft --recurse-submodules HEAD~1' 'option'
}

@test "a soft reset during a rebase, merge, cherry-pick, or revert is denied" {
  local marker git_dir
  git_dir="${WORK}/.git"
  for marker in rebase-merge rebase-apply sequencer; do
    mkdir "${git_dir}/${marker}"
    assert_denied_because 'git reset --soft HEAD~1' 'in progress'
    rmdir "${git_dir}/${marker}"
  done
  for marker in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD; do
    git -C "${WORK}" rev-parse HEAD >"${git_dir}/${marker}"
    assert_denied_because 'git reset --soft HEAD~1' 'in progress'
    rm -f "${git_dir}/${marker}"
  done
  assert_silent_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "a soft reset on a detached HEAD is denied" {
  git -C "${WORK}" checkout -q --detach
  assert_denied_because 'git reset --soft HEAD~1' 'detached'
}

@test "a soft reset on the default branch named by origin/HEAD is denied" {
  git -C "${WORK}" checkout -q main
  commit_file local-only
  assert_denied_because 'git reset --soft HEAD~1' 'default branch'
}

@test "a soft reset on the branch origin/HEAD names is denied when it is not main" {
  git -C "${WORK}" push -q origin main:trunk
  git -C "${WORK}" fetch -q origin
  git -C "${WORK}" remote set-head origin trunk
  git -C "${WORK}" checkout -q -b trunk origin/trunk
  commit_file trunk-local
  assert_denied_because 'git reset --soft HEAD~1' 'default branch'
  git -C "${WORK}" checkout -q feature
  assert_silent_in "${WORK}" 'git reset --soft HEAD~2'
}

@test "main and master count as default when origin/HEAD is not set" {
  git -C "${WORK}" remote set-head origin --delete
  git -C "${WORK}" checkout -q main
  commit_file local-only
  assert_denied_because 'git reset --soft HEAD~1' 'default branch'
  git -C "${WORK}" checkout -q -b master
  assert_denied_because 'git reset --soft HEAD~1' 'default branch'
  git -C "${WORK}" checkout -q feature
  assert_silent_in "${WORK}" 'git reset --soft HEAD~2'
}

@test "a soft reset to a revision that does not resolve is denied" {
  assert_denied_because 'git reset --soft no-such-ref' 'resolve'
}

@test "a soft reset to a commit that is not an ancestor of HEAD is denied" {
  git -C "${WORK}" checkout -q -b elsewhere main
  commit_file elsewhere
  git -C "${WORK}" checkout -q feature
  assert_denied_because 'git reset --soft elsewhere' 'ancestor'
}

@test "a soft reset that rewinds a pushed commit is denied" {
  git -C "${WORK}" push -q origin feature
  assert_denied_because 'git reset --soft HEAD~1' 'pushed'
}

@test "a soft reset past the pushed part of the branch is denied, short of it allowed" {
  git -C "${WORK}" push -q origin feature
  commit_file three
  assert_denied_because 'git reset --soft HEAD~2' 'pushed'
  assert_silent_in "${WORK}" 'git reset --soft HEAD~1'
}

@test "a soft reset of commits another remote-tracking ref holds is denied" {
  git -C "${WORK}" remote add backup "${REMOTE}"
  git -C "${WORK}" push -q backup feature
  git -C "${WORK}" fetch -q backup
  assert_denied_because 'git reset --soft HEAD~1' 'pushed'
}

@test "an operand with a variable, glob, substitution, or reflog brace is denied" {
  assert_denies_in "${WORK}" 'git reset --soft $PARENT'
  assert_denies_in "${WORK}" 'git reset --soft "$PARENT"'
  assert_denies_in "${WORK}" 'git reset --soft HEAD~*'
  assert_denies_in "${WORK}" 'git reset --soft $(git merge-base HEAD main)'
  assert_denies_in "${WORK}" 'git reset --soft `git merge-base HEAD main`'
  assert_denies_in "${WORK}" 'git reset --soft HEAD@{1}'
  assert_denies_in "${WORK}" 'git reset --soft ~/HEAD'
}

@test "a directory that is no repository is denied" {
  mkdir "${BATS_TEST_TMPDIR}/plain"
  assert_denies_in "${BATS_TEST_TMPDIR}/plain" 'git reset --soft HEAD~1'
  assert_reason_contains 'step squash'
}

@test "a -C path that does not exist is denied" {
  assert_denies_in "${WORK}" "git -C ${BATS_TEST_TMPDIR}/missing reset --soft HEAD~1"
}

@test "a -C path with a variable is denied" {
  assert_denies_in "${WORK}" 'git -C $REPO reset --soft HEAD~1'
}

@test "a command with no cwd and no -C is denied" {
  assert_denies 'git reset --soft HEAD~1'
  assert_reason_contains 'working directory'
}

@test "a relative -C with no cwd is denied" {
  assert_denies 'git -C work reset --soft HEAD~1'
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

@test "a global option that changes which repository git reads is denied" {
  assert_denies_in "${WORK}" "git --git-dir=${WORK}/.git reset --soft HEAD~1"
  assert_denies_in "${WORK}" "git --work-tree=${WORK} reset --soft HEAD~1"
  assert_denies_in "${WORK}" 'git -c core.x=y reset --soft HEAD~1'
}

@test "a GIT_ variable set for the command is denied" {
  assert_denies_in "${WORK}" "GIT_DIR=${WORK}/.git git reset --soft HEAD~1"
  assert_denies_in "${WORK}" "env GIT_WORK_TREE=${WORK} git reset --soft HEAD~1"
}

@test "a soft reset after a directory change is denied" {
  assert_denies_in "${BATS_TEST_TMPDIR}" "cd ${WORK} && git reset --soft HEAD~1"
  assert_reason_contains 'changes directory'
}

@test "a soft reset behind env -C is denied" {
  assert_denies_in "${WORK}" "env -C ${BATS_TEST_TMPDIR} git reset --soft HEAD~1"
}

@test "a soft reset after another step is denied" {
  assert_denies_in "${WORK}" 'git status && git reset --soft HEAD~1'
  assert_reason_contains 'follows another step'
  assert_denies_in "${WORK}" 'git push; git reset --soft HEAD~1'
  assert_denies_in "${WORK}" 'git reset --soft HEAD~1 && git reset --soft HEAD~1'
}

@test "a soft reset after a separator on the default branch is denied" {
  git -C "${WORK}" checkout -q main
  commit_file local-only
  assert_denies_in "${WORK}" 'true || git reset --soft HEAD~1'
  assert_denies_in "${WORK}" $'true\ngit reset --soft HEAD~1'
}

@test "a soft reset in a sh -c string on the default branch is denied" {
  git -C "${WORK}" checkout -q main
  commit_file local-only
  assert_denied_because "sh -c 'git reset --soft HEAD~1'" 'default branch'
}

@test "a soft reset behind env on the default branch is denied" {
  git -C "${WORK}" checkout -q main
  commit_file local-only
  assert_denied_because 'env FOO=1 git reset --soft HEAD~1' 'default branch'
}

@test "a soft reset by -C on the default branch is denied" {
  git -C "${WORK}" checkout -q main
  commit_file local-only
  assert_denies_in "${BATS_TEST_TMPDIR}" "git -C ${WORK} reset --soft HEAD~1"
  assert_reason_contains 'default branch'
}

@test "a step after the soft reset does not hold it back" {
  assert_silent_in "${WORK}" 'git reset --soft HEAD~1; echo done'
}
