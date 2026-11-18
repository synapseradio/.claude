# The scratch remote and clone for the deny-unsafe-soft-reset tests, built
# once per file and copied per case.
#
# shellcheck shell=bash

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
