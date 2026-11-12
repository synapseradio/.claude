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

# The single-quoted command texts below are the input under test, so their
# $ and backticks must stay literal (SC2016). bats reads BATS_TEST_TIMEOUT
# and the helpers read HOOK, which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

BATS_TEST_TIMEOUT=10

setup() {
  export HOME="${BATS_TEST_TMPDIR}/home"
  export XDG_CONFIG_HOME="${HOME}/.config"
  export XDG_DATA_HOME="${HOME}/.local/share"
  export XDG_CACHE_HOME="${HOME}/.cache"
  export GIT_CONFIG_GLOBAL="${HOME}/.gitconfig"
  export GIT_CONFIG_NOSYSTEM=1
  mkdir -p "${HOME}"
  printf '[user]\n\tname = Test\n\temail = test@example.com\n' \
    >"${GIT_CONFIG_GLOBAL}"
  # A hook run from a linked worktree inherits these, and a scratch
  # repository that kept them would write into the repository that holds
  # the tests.
  unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_COMMON_DIR \
    GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_NAMESPACE \
    GIT_CEILING_DIRECTORIES
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-rm.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
}

#######################################
# Build a scratch repository whose every file is committed and unchanged.
# Globals:
#   REPO, BATS_TEST_TMPDIR
#######################################
make_repo() {
  REPO="${BATS_TEST_TMPDIR}/repo"
  git init -q -b main "${REPO}"
  mkdir -p "${REPO}/dir/sub" "${REPO}/sub"
  printf 'one\n' >"${REPO}/tracked.txt"
  printf 'two\n' >"${REPO}/other.txt"
  printf 'three\n' >"${REPO}/a b.txt"
  printf 'four\n' >"${REPO}/-x"
  printf 'five\n' >"${REPO}/dir/one.txt"
  printf 'six\n' >"${REPO}/dir/sub/two.txt"
  printf 'seven\n' >"${REPO}/sub/inner.txt"
  printf '*.log\n__pycache__/\n' >"${REPO}/.gitignore"
  git -C "${REPO}" add -A
  git -C "${REPO}" commit -q -m seed
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

@test "a bare rm is denied" {
  assert_denies 'rm notes.txt'
}

@test "rm with flags is denied" {
  assert_denies 'rm -rf build/'
}

@test "rm named by path is denied" {
  assert_denies '/bin/rm notes.txt'
}

@test "rm after && is denied" {
  assert_denies 'cd build && rm -rf out'
}

@test "rm after || is denied" {
  assert_denies 'make clean || rm -rf out'
}

@test "rm after a semicolon is denied" {
  assert_denies 'npm run build; rm -rf dist'
}

@test "rm after a pipe is denied" {
  assert_denies 'ls *.tmp | rm'
}

@test "rm on a later line is denied" {
  assert_denies $'cd build\nrm -rf out'
}

@test "rm inside a subshell is denied" {
  assert_denies '(cd build && rm -rf out)'
}

@test "rm inside a command substitution is denied" {
  assert_denies 'echo $(rm -rf out)'
}

@test "rm inside backticks is denied" {
  assert_denies 'echo `rm -rf out`'
}

@test "rm inside a double-quoted command substitution is denied" {
  assert_denies 'echo "done: $(rm -rf out)"'
}

@test "rm behind sudo is denied" {
  assert_denies 'sudo rm -rf /etc/hosts'
}

@test "rm behind sudo with a user option is denied" {
  assert_denies 'sudo -u root rm notes.txt'
}

@test "rm behind command is denied" {
  assert_denies 'command rm notes.txt'
}

@test "rm behind xargs is denied" {
  assert_denies 'ls *.tmp | xargs rm'
}

@test "rm behind xargs with a replacement option is denied" {
  assert_denies 'ls | xargs -I {} rm {}'
}

@test "rm behind env is denied" {
  assert_denies 'env rm notes.txt'
}

@test "rm behind env with an assignment is denied" {
  assert_denies 'env LC_ALL=C rm notes.txt'
}

@test "rm behind exec is denied" {
  assert_denies 'exec rm notes.txt'
}

@test "rm behind a variable assignment is denied" {
  assert_denies 'TMPDIR=/tmp rm notes.txt'
}

@test "rm inside a loop body is denied" {
  assert_denies 'for f in a b; do rm "$f"; done'
}

@test "rm after then is denied" {
  assert_denies 'if [ -f x ]; then rm x; fi'
}

@test "rm in a bash -c string is denied" {
  assert_denies "bash -c 'echo start; rm notes.txt'"
}

@test "rm behind find -exec is denied" {
  assert_denies 'find . -name "*.tmp" -exec rm {} \;'
}

@test "a backslash-escaped rm is denied" {
  assert_denies '\rm notes.txt'
}

@test "a quoted command word rm is denied" {
  assert_denies '"rm" notes.txt'
}

@test "a denial points at trash" {
  run_bash_hook 'rm notes.txt'
  [[ "$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")" == *'trash <path>'* ]]
}

@test "git rm stays silent" {
  assert_silent 'git rm --cached notes.txt'
}

@test "bun rm stays silent" {
  assert_silent 'bun rm left-pad'
}

@test "npm rm stays silent" {
  assert_silent 'npm rm left-pad'
}

@test "pnpm rm stays silent" {
  assert_silent 'pnpm rm left-pad'
}

@test "docker rm stays silent" {
  assert_silent 'docker rm -f web'
}

@test "trash stays silent" {
  assert_silent 'trash notes.txt'
}

@test "rmdir stays silent" {
  assert_silent 'rmdir empty-dir'
}

@test "rm as an argument to echo stays silent" {
  assert_silent 'echo rm'
}

@test "rm as an argument to grep stays silent" {
  assert_silent 'grep -n rm file'
}

@test "rm inside a double-quoted string stays silent" {
  assert_silent 'echo "rm -rf build/"'
}

@test "rm inside a single-quoted string stays silent" {
  assert_silent "echo 'run rm -rf build/ later'"
}

@test "rm in a commit message stays silent" {
  assert_silent 'git commit -m "feat: replace rm with trash"'
}

@test "rm after a command substitution inside quotes stays silent" {
  assert_silent 'echo "built $(date) rm done"'
}

@test "rm at the start of a here-document line stays silent" {
  assert_silent $'cat <<\'EOF\'\nrm notes.txt\nEOF'
}

@test "rm in a comment stays silent" {
  assert_silent $'ls # rm notes.txt\npwd'
}

@test "command -v rm stays silent" {
  assert_silent 'command -v rm'
}

@test "a word starting with rm stays silent" {
  assert_silent 'rm-tool --help'
}

@test "a file named rm stays silent" {
  assert_silent 'cat docs/rm.md'
}

@test "an empty command stays silent" {
  assert_silent ''
}

@test "a denial says rm runs only on files committed and unchanged in git" {
  run_bash_hook 'rm notes.txt'
  assert_reason_contains 'committed and unchanged in git'
}

# What git can restore

@test "rm of a committed unchanged file is allowed" {
  make_repo
  assert_silent "rm ${REPO}/tracked.txt"
}

@test "rm -f of a committed unchanged file is allowed" {
  make_repo
  assert_silent "rm -f ${REPO}/tracked.txt"
}

@test "rm of a modified file is denied and names the file" {
  make_repo
  printf 'edited\n' >>"${REPO}/tracked.txt"
  run_bash_hook "rm ${REPO}/tracked.txt"
  assert_decision 'deny' "modified file"
  assert_reason_contains "${REPO}/tracked.txt"
  assert_reason_contains 'trash <path>'
}

@test "rm of a staged edit is denied" {
  make_repo
  printf 'edited\n' >>"${REPO}/tracked.txt"
  git -C "${REPO}" add tracked.txt
  assert_denies "rm ${REPO}/tracked.txt"
}

@test "rm of a newly staged file is denied" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  git -C "${REPO}" add new.txt
  assert_denies "rm ${REPO}/new.txt"
}

@test "rm of an untracked file is denied" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  assert_denies "rm ${REPO}/new.txt"
}

@test "rm of an ignored file is denied" {
  make_repo
  printf 'log\n' >"${REPO}/build.log"
  assert_denies "rm ${REPO}/build.log"
}

@test "rm of a file whose edits git was told to ignore is denied" {
  make_repo
  git -C "${REPO}" update-index --assume-unchanged tracked.txt
  printf 'edited\n' >>"${REPO}/tracked.txt"
  assert_denies "rm ${REPO}/tracked.txt"
}

@test "rm of a file deleted from the index but still on disk is denied" {
  make_repo
  git -C "${REPO}" rm -q --cached tracked.txt
  assert_denies "rm ${REPO}/tracked.txt"
}

@test "rm -r of a committed unchanged directory is allowed" {
  make_repo
  assert_silent "rm -r ${REPO}/dir"
}

@test "rm -rf of a committed unchanged directory with a trailing slash is allowed" {
  make_repo
  assert_silent "rm -rf ${REPO}/dir/"
}

@test "rm -r of a directory holding a modified file is denied" {
  make_repo
  printf 'edited\n' >>"${REPO}/dir/sub/two.txt"
  assert_denies "rm -r ${REPO}/dir"
}

@test "rm -r of a directory holding an untracked file is denied" {
  make_repo
  printf 'new\n' >"${REPO}/dir/sub/new.txt"
  run_bash_hook "rm -r ${REPO}/dir"
  assert_decision 'deny' "untracked file beneath"
  assert_reason_contains "${REPO}/dir"
}

@test "rm -r of a directory holding an ignored file is denied" {
  make_repo
  mkdir "${REPO}/dir/__pycache__"
  printf 'bytecode\n' >"${REPO}/dir/__pycache__/x.pyc"
  assert_denies "rm -r ${REPO}/dir"
}

@test "rm -r of a directory holding a nested repository is denied" {
  make_repo
  git init -q "${REPO}/dir/nested"
  assert_denies "rm -r ${REPO}/dir"
}

@test "rm -r of a directory holding a submodule is denied" {
  make_repo
  local sha
  sha="$(git -C "${REPO}" rev-parse HEAD)"
  git -C "${REPO}" update-index --add --cacheinfo "160000,${sha},dir/mod"
  git -C "${REPO}" commit -q -m 'add a gitlink'
  mkdir "${REPO}/dir/mod"
  assert_denies "rm -r ${REPO}/dir"
}

@test "rm -r of an untracked directory is denied" {
  make_repo
  mkdir "${REPO}/scratch"
  printf 'x\n' >"${REPO}/scratch/x.txt"
  assert_denies "rm -r ${REPO}/scratch"
}

@test "rm -rf of a repository root is denied" {
  make_repo
  assert_denies "rm -rf ${REPO}"
}

@test "rm -rf of a repository's git directory is denied" {
  make_repo
  assert_denies "rm -rf ${REPO}/.git"
}

@test "rm of a file inside a git directory is denied" {
  make_repo
  assert_denies "rm ${REPO}/.git/HEAD"
}

@test "rm of a file outside any repository is denied" {
  make_plain_dir
  run_bash_hook "rm ${PLAIN}/loose.txt"
  assert_decision 'deny' "plain directory"
  assert_reason_contains "${PLAIN}/loose.txt"
}

@test "rm -rf of a directory outside any repository is denied" {
  make_plain_dir
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

@test "rm of a committed symlink is allowed" {
  make_repo
  ln -s dir "${REPO}/link"
  git -C "${REPO}" add link
  git -C "${REPO}" commit -q -m 'add link'
  assert_silent "rm ${REPO}/link"
}

# Operands the guard cannot read

@test "a relative operand resolves against the envelope's cwd" {
  make_repo
  assert_silent_in "${REPO}" 'rm tracked.txt'
  assert_silent_in "${REPO}/sub" 'rm ../tracked.txt'
}

@test "a relative operand naming an untracked file is denied from the cwd" {
  make_repo
  printf 'new\n' >"${REPO}/sub/new.txt"
  assert_denies_in "${REPO}/sub" 'rm new.txt'
}

@test "a relative operand outside any repository is denied from the cwd" {
  make_plain_dir
  assert_denies_in "${PLAIN}" 'rm loose.txt'
}

@test "a relative operand with no cwd in the envelope is denied" {
  make_repo
  assert_denies 'rm tracked.txt'
}

@test "an operand holding a glob is denied" {
  make_repo
  assert_denies_in "${REPO}" 'rm *.txt'
  assert_denies_in "${REPO}" 'rm tracked.tx?'
  assert_denies_in "${REPO}" 'rm [t]racked.txt'
}

@test "an operand holding a variable is denied" {
  make_repo
  assert_denies_in "${REPO}" 'rm "$FILE"'
  assert_denies_in "${REPO}" 'rm ${FILE}'
}

@test "an operand holding a command substitution is denied" {
  make_repo
  assert_denies_in "${REPO}" 'rm $(echo tracked.txt)'
  assert_denies_in "${REPO}" 'rm `echo tracked.txt`'
}

@test "an operand holding a tilde is denied" {
  make_repo
  assert_denies_in "${REPO}" 'rm ~/tracked.txt'
}

@test "an operand holding a brace expansion is denied" {
  make_repo
  assert_denies_in "${REPO}" 'rm {tracked,other}.txt'
}

@test "rm with no operand is denied" {
  make_repo
  assert_denies_in "${REPO}" 'rm'
  assert_denies_in "${REPO}" 'rm -rf'
}

@test "rm of a repository's own root by dot is denied" {
  make_repo
  assert_denies_in "${REPO}" 'rm -rf .'
  assert_denies_in "${REPO}/sub" 'rm -rf ..'
}

@test "rm of a quoted path with a space is judged by that path" {
  make_repo
  assert_silent_in "${REPO}" 'rm "a b.txt"'
  printf 'x\n' >"${REPO}/c d.txt"
  assert_denies_in "${REPO}" "rm 'c d.txt'"
}

@test "rm after -- judges an operand that starts with a dash" {
  make_repo
  assert_silent_in "${REPO}" 'rm -- -x'
}

@test "rm with output redirects is judged by its operands alone" {
  make_repo
  assert_silent_in "${REPO}" 'rm tracked.txt 2>/dev/null'
  assert_silent_in "${REPO}" 'rm -f tracked.txt >/dev/null 2>&1'
}

@test "rm with a redirect to a file is denied" {
  make_repo
  assert_denies_in "${REPO}" 'rm tracked.txt > out.log'
}

@test "rm of two operands is denied when one is untracked" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  run_bash_hook "rm ${REPO}/tracked.txt ${REPO}/new.txt"
  assert_decision 'deny' "mixed operands"
  assert_reason_contains "${REPO}/new.txt"
}

@test "rm of two committed unchanged operands is allowed" {
  make_repo
  assert_silent "rm ${REPO}/tracked.txt ${REPO}/other.txt"
}

@test "rm of a path that does not exist is allowed" {
  make_repo
  assert_silent "rm ${REPO}/missing.txt"
  assert_silent "rm -f ${REPO}/missing.txt"
}

@test "rm of a missing path beside an untracked file is denied" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  assert_denies "rm -f ${REPO}/missing.txt ${REPO}/new.txt"
}

# Where the guard cannot tell what the operands are

@test "rm after a cd is denied" {
  make_repo
  assert_denies "cd ${REPO} && rm tracked.txt"
}

@test "rm after a cd in a subshell is denied" {
  make_repo
  assert_denies "(cd ${REPO} && rm tracked.txt)"
}

@test "rm after pushd is denied" {
  make_repo
  assert_denies "pushd ${REPO}; rm tracked.txt"
}

@test "rm behind env -C is denied" {
  make_repo
  assert_denies_in "${REPO}/sub" 'env -C .. rm tracked.txt'
}

@test "rm behind sudo -D is denied" {
  make_repo
  assert_denies_in "${REPO}/sub" 'sudo -D .. rm tracked.txt'
}

@test "rm behind xargs is denied even with a named file" {
  make_repo
  assert_denies "echo more | xargs rm ${REPO}/tracked.txt"
}

@test "rm behind find -exec is denied even with absolute operands" {
  make_repo
  assert_denies "find ${REPO} -name x -exec rm ${REPO}/tracked.txt \\;"
}

@test "rm behind find -execdir is denied" {
  make_repo
  assert_denies "find ${REPO} -name x -execdir rm tracked.txt \\;"
}

# Command positions still judged by the rule

@test "rm after && is judged by the rule" {
  make_repo
  assert_silent "true && rm ${REPO}/tracked.txt"
  printf 'new\n' >"${REPO}/new.txt"
  assert_denies "true && rm ${REPO}/new.txt"
}

@test "rm after || and ; and a pipe is judged by the rule" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  assert_silent "false || rm ${REPO}/tracked.txt"
  assert_silent "true; rm ${REPO}/tracked.txt"
  assert_silent "echo x | rm ${REPO}/tracked.txt"
  assert_denies "false || rm ${REPO}/new.txt"
  assert_denies "true; rm ${REPO}/new.txt"
}

@test "rm on a later line is judged by the rule" {
  make_repo
  assert_silent $'echo go\n'"rm ${REPO}/tracked.txt"
}

@test "rm in a subshell and a command substitution is judged by the rule" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  assert_silent "(rm ${REPO}/tracked.txt)"
  assert_silent "echo \$(rm ${REPO}/tracked.txt)"
  assert_denies "(rm ${REPO}/new.txt)"
  assert_denies "echo \$(rm ${REPO}/new.txt)"
}

@test "rm behind each wrapper word is judged by the rule" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  local wrapper
  for wrapper in 'sudo' 'sudo -u root' 'command' 'env' 'env LC_ALL=C' 'exec' 'nohup' 'time'; do
    assert_silent "${wrapper} rm ${REPO}/tracked.txt"
    assert_denies "${wrapper} rm ${REPO}/new.txt"
  done
}

@test "rm inside a loop body and after then is judged by the rule" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  assert_silent "for f in a b; do rm ${REPO}/tracked.txt; done"
  assert_silent "if true; then rm ${REPO}/tracked.txt; fi"
  assert_denies "for f in a b; do rm ${REPO}/new.txt; done"
  assert_denies "if true; then rm ${REPO}/new.txt; fi"
}

@test "rm in a bash -c string is judged by the rule" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  assert_silent "bash -c 'echo start; rm ${REPO}/tracked.txt'"
  assert_denies "bash -c 'echo start; rm ${REPO}/new.txt'"
}

@test "rm in a bash -c string after a cd is denied" {
  make_repo
  assert_denies "bash -c 'cd ${REPO}; rm tracked.txt'"
}

# Failing closed

@test "rm is denied when git does not answer before the deadline" {
  make_repo
  local stubs="${BATS_TEST_TMPDIR}/stubs"
  mkdir -p "${stubs}"
  printf '#!/bin/bash\nexec sleep 10\n' >"${stubs}/git"
  chmod +x "${stubs}/git"
  PATH="${stubs}:${PATH}" WARDEN_RM_DEADLINE=1 \
    assert_denies "rm ${REPO}/tracked.txt"
}

@test "rm is denied when git is not installed" {
  make_repo
  local stubs="${BATS_TEST_TMPDIR}/stubs"
  mkdir -p "${stubs}"
  printf '#!/bin/bash\nexit 127\n' >"${stubs}/git"
  chmod +x "${stubs}/git"
  PATH="${stubs}:${PATH}" assert_denies "rm ${REPO}/tracked.txt"
}
