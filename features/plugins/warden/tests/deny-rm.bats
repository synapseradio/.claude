#!/usr/bin/env bats
#
# Tests for deny-rm.sh, the PreToolUse Bash guard that lets rm run only on
# paths git can restore and points everything else at trash.
#
# The first group covers rm at each command position against paths git has
# no copy of: alone, after each separator, in a subshell and a command
# substitution, behind each wrapper word, inside a loop body, in a shell -c
# string, and behind find -exec. The silent cases cover the other programs
# that spell rm as a subcommand, the neighbors trash and rmdir, and the word
# rm as an argument, inside a quoted string, in a comment, and in a
# here-document body. The second group builds scratch git repositories and
# covers what the guard decides from git's view of each operand.
# deny-rm-command.bats covers rm's place in the command, git failing, and
# the envelope.

# The single-quoted command texts below are the input under test, so their
# $ and backticks must stay literal (SC2016). bats reads BATS_TEST_TIMEOUT,
# which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

BATS_TEST_TIMEOUT=10

setup_file() {
  export FIXTURE="${BATS_FILE_TMPDIR}/repo"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load "${BATS_TEST_DIRNAME}/deny-rm-fixture.bash"
  export HOME="${BATS_FILE_TMPDIR}/home"
  mkdir -p "${HOME}"
  isolate_git_config
  build_fixture
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load "${BATS_TEST_DIRNAME}/deny-rm-fixture.bash"
  load_guard deny-rm
  isolate_home
  isolate_git_config
}

@test "rm is denied in each spelling" {
  local -a forms=(
    'rm notes.txt'
    'rm -rf build/'
    '/bin/rm notes.txt'
    '\rm notes.txt'
    '"rm" notes.txt'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "rm is denied after each separator and inside each grouping" {
  local -a forms=(
    'cd build && rm -rf out'
    'make clean || rm -rf out'
    'npm run build; rm -rf dist'
    'ls *.tmp | rm'
    $'cd build\nrm -rf out'
    '(cd build && rm -rf out)'
    'echo $(rm -rf out)'
    'echo `rm -rf out`'
    'echo "done: $(rm -rf out)"'
    'for f in a b; do rm "$f"; done'
    'if [ -f x ]; then rm x; fi'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "rm is denied behind each wrapper word, xargs, find -exec, and in a shell string" {
  local -a forms=(
    'sudo rm -rf /etc/hosts'
    'sudo -u root rm notes.txt'
    'command rm notes.txt'
    'ls *.tmp | xargs rm'
    'ls | xargs -I {} rm {}'
    'env rm notes.txt'
    'env LC_ALL=C rm notes.txt'
    'exec rm notes.txt'
    'TMPDIR=/tmp rm notes.txt'
    "bash -c 'echo start; rm notes.txt'"
    'find . -name "*.tmp" -exec rm {} \;'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "other programs that spell rm as a subcommand, and the neighbors trash and rmdir, stay silent" {
  local -a forms=(
    'git rm --cached notes.txt'
    'bun rm left-pad'
    'npm rm left-pad'
    'pnpm rm left-pad'
    'docker rm -f web'
    'trash notes.txt'
    'rmdir empty-dir'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "the word rm as an argument, inside a string, in a comment, or in a longer word stays silent" {
  local -a forms=(
    'echo rm'
    'grep -n rm file'
    'echo "rm -rf build/"'
    "echo 'run rm -rf build/ later'"
    'git commit -m "feat: replace rm with trash"'
    'echo "built $(date) rm done"'
    $'cat <<\'EOF\'\nrm notes.txt\nEOF'
    $'ls # rm notes.txt\npwd'
    'command -v rm'
    'rm-tool --help'
    'cat docs/rm.md'
    ''
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "rm of paths git can restore is allowed" {
  make_repo
  ln -s dir "${REPO}/link"
  git -C "${REPO}" add link
  git -C "${REPO}" commit -q -m 'add link'
  local -a forms=(
    "rm ${REPO}/tracked.txt"
    "rm -f ${REPO}/tracked.txt"
    "rm ${REPO}/tracked.txt ${REPO}/other.txt"
    "rm -r ${REPO}/dir"
    "rm -rf ${REPO}/dir/"
    "rm ${REPO}/link"
    "rm ${REPO}/missing.txt"
    "rm -f ${REPO}/missing.txt"
    "rm ${REPO}/tracked.txt && rm ${REPO}/other.txt"
    "rm ${REPO}/tracked.txt; rm -r ${REPO}/dir"
    "rm ${REPO}/tracked.txt || rm ${REPO}/other.txt"
    $'rm '"${REPO}"$'/tracked.txt\nrm '"${REPO}"'/other.txt'
    "rm ${REPO}/tracked.txt && echo done"
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "rm of a file git cannot restore is denied" {
  make_repo
  printf 'edited\n' >>"${REPO}/tracked.txt"
  printf 'edited\n' >>"${REPO}/other.txt"
  git -C "${REPO}" add other.txt
  printf 'new\n' >"${REPO}/staged.txt"
  git -C "${REPO}" add staged.txt
  printf 'new\n' >"${REPO}/untracked.txt"
  printf 'log\n' >"${REPO}/build.log"
  git -C "${REPO}" update-index --assume-unchanged sub/inner.txt
  printf 'edited\n' >>"${REPO}/sub/inner.txt"
  git -C "${REPO}" rm -q --cached dir/one.txt
  local -a files=(
    tracked.txt other.txt staged.txt untracked.txt build.log sub/inner.txt
    dir/one.txt
  )
  local file
  for file in "${files[@]}"; do
    assert_denies "rm ${REPO}/${file}"
  done
}

@test "rm -r of a directory git cannot fully restore is denied" {
  make_repo
  local dir sha
  for dir in modified untracked ignored nested submodule; do
    mkdir "${REPO}/${dir}"
    printf 'x\n' >"${REPO}/${dir}/f.txt"
  done
  git -C "${REPO}" add -A
  git -C "${REPO}" commit -q -m 'add directories'
  printf 'edited\n' >>"${REPO}/modified/f.txt"
  printf 'new\n' >"${REPO}/untracked/new.txt"
  mkdir "${REPO}/ignored/__pycache__"
  printf 'bytecode\n' >"${REPO}/ignored/__pycache__/x.pyc"
  git init -q "${REPO}/nested/inner"
  sha="$(git -C "${REPO}" rev-parse HEAD)"
  git -C "${REPO}" update-index --add --cacheinfo "160000,${sha},submodule/mod"
  git -C "${REPO}" commit -q -m 'add a gitlink'
  mkdir "${REPO}/submodule/mod" "${REPO}/scratch"
  printf 'x\n' >"${REPO}/scratch/x.txt"
  for dir in modified untracked ignored nested submodule scratch; do
    assert_denies "rm -r ${REPO}/${dir}"
  done
  assert_denies "rm -rf ${REPO}"
  assert_denies "rm -rf ${REPO}/.git"
  assert_denies "rm ${REPO}/.git/HEAD"
}

@test "rm of a path outside any repository is denied" {
  make_plain_dir
  assert_denies "rm ${PLAIN}/loose.txt"
  assert_denies "rm -rf ${PLAIN}"
}

@test "rm of a committed file in another repository is allowed" {
  make_repo
  local other="${BATS_TEST_TMPDIR}/other-repo"
  git init -q -b main "${other}"
  printf 'x\n' >"${other}/kept.txt"
  git -C "${other}" add kept.txt
  git -C "${other}" commit -q -m seed
  assert_silent "rm ${REPO}/tracked.txt ${other}/kept.txt"
}

@test "rm judges the path's own repository when GIT_DIR names another" {
  make_repo
  local other="${BATS_TEST_TMPDIR}/other-repo"
  git init -q -b main "${other}"
  GIT_DIR="${other}/.git" GIT_WORK_TREE="${other}" assert_silent "rm ${REPO}/tracked.txt"
}

@test "rm of a symlink that points into a committed directory with a trailing slash is denied" {
  make_repo
  ln -s dir "${REPO}/link"
  git -C "${REPO}" add link
  git -C "${REPO}" commit -q -m 'add link'
  assert_denies "rm -rf ${REPO}/link/"
}

@test "a relative operand is judged against the envelope's cwd, and denied where there is none" {
  make_repo
  make_plain_dir
  printf 'new\n' >"${REPO}/sub/new.txt"
  assert_silent_in "${REPO}" 'rm tracked.txt'
  assert_silent_in "${REPO}/sub" 'rm ../tracked.txt'
  assert_denies_in "${REPO}/sub" 'rm new.txt'
  assert_denies_in "${PLAIN}" 'rm loose.txt'
  assert_denies 'rm tracked.txt'
  assert_denies_in '' 'rm tracked.txt'
  assert_silent_in '' "rm ${REPO}/tracked.txt"
}

@test "every line of a multi-line command is judged, with or without a cwd" {
  make_repo
  printf 'new\n' >"${REPO}/untracked.txt"
  assert_silent_in "${REPO}" $'rm tracked.txt\nrm other.txt'
  assert_denies_in "${REPO}" $'rm tracked.txt\nrm other.txt\nrm untracked.txt'
  assert_silent $'rm '"${REPO}"$'/tracked.txt\nrm '"${REPO}"'/other.txt'
  assert_denies $'rm '"${REPO}"$'/tracked.txt\nrm relative.txt'
}

@test "an operand the guard cannot read is denied" {
  make_repo
  local -a forms=(
    'rm *.txt'
    'rm tracked.tx?'
    'rm [t]racked.txt'
    'rm "$FILE"'
    'rm ${FILE}'
    'rm $(echo tracked.txt)'
    'rm `echo tracked.txt`'
    'rm ~/tracked.txt'
    'rm {tracked,other}.txt'
    'rm'
    'rm -rf'
    'rm tracked.txt > out.log'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies_in "${REPO}" "${form}"
  done
}

@test "rm of a repository's own root by dot is denied" {
  make_repo
  assert_denies_in "${REPO}" 'rm -rf .'
  assert_denies_in "${REPO}/sub" 'rm -rf ..'
}

@test "rm of a quoted untracked path with a space is denied" {
  make_repo
  printf 'x\n' >"${REPO}/c d.txt"
  assert_denies_in "${REPO}" "rm 'c d.txt'"
}

@test "rm judges its operands alone: a quoted space, a dash operand, and output redirects" {
  make_repo
  local -a forms=(
    'rm -- -x'
    'rm tracked.txt 2>/dev/null'
    'rm -f tracked.txt >/dev/null 2>&1'
    'rm "a b.txt"'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent_in "${REPO}" "${form}"
  done
}

@test "rm is denied when one of its operands is untracked" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  assert_denies "rm ${REPO}/tracked.txt ${REPO}/new.txt"
  assert_denies "rm -f ${REPO}/missing.txt ${REPO}/new.txt"
}

@test "rm after a directory change is denied" {
  make_repo
  assert_denies "cd ${REPO} && rm tracked.txt"
  assert_denies "(cd ${REPO} && rm tracked.txt)"
  assert_denies "pushd ${REPO}; rm tracked.txt"
  assert_denies "bash -c 'cd ${REPO}; rm tracked.txt'"
  assert_denies_in "${REPO}/sub" 'env -C .. rm tracked.txt'
  assert_denies_in "${REPO}/sub" 'sudo -D .. rm tracked.txt'
}

@test "rm run by xargs or find is denied even with named operands" {
  make_repo
  local -a forms=(
    "echo more | xargs rm ${REPO}/tracked.txt"
    "find ${REPO} -name x -exec rm ${REPO}/tracked.txt \\;"
    "find ${REPO} -name x -execdir rm tracked.txt \\;"
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}
