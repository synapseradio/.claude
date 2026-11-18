# Scratch repositories for the deny-rm tests: one built per file, a copy
# per case, and a directory outside any repository.
#
# shellcheck shell=bash

#######################################
# Build, once for the file, a scratch repository whose every file is
# committed and unchanged.
# Globals:
#   FIXTURE
#######################################
build_fixture() {
  git init -q -b main "${FIXTURE}"
  mkdir -p "${FIXTURE}/dir/sub" "${FIXTURE}/sub"
  printf 'one\n' >"${FIXTURE}/tracked.txt"
  printf 'two\n' >"${FIXTURE}/other.txt"
  printf 'three\n' >"${FIXTURE}/a b.txt"
  printf 'four\n' >"${FIXTURE}/-x"
  printf 'five\n' >"${FIXTURE}/dir/one.txt"
  printf 'six\n' >"${FIXTURE}/dir/sub/two.txt"
  printf 'seven\n' >"${FIXTURE}/sub/inner.txt"
  printf '*.log\n__pycache__/\n' >"${FIXTURE}/.gitignore"
  git -C "${FIXTURE}" add -A
  git -C "${FIXTURE}" commit -q -m seed
}

#######################################
# Give this case its own copy of the file's scratch repository.
# Globals:
#   FIXTURE, REPO, BATS_TEST_TMPDIR
#######################################
make_repo() {
  REPO="${BATS_TEST_TMPDIR}/repo"
  cp -R "${FIXTURE}" "${REPO}"
}

#######################################
# Make a directory that sits in no repository.
# Globals:
#   PLAIN, BATS_TEST_TMPDIR
#######################################
make_plain_dir() {
  PLAIN="${BATS_TEST_TMPDIR}/plain"
  mkdir -p "${PLAIN}"
  printf 'loose\n' >"${PLAIN}/loose.txt"
}
