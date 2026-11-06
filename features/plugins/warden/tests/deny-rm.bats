#!/usr/bin/env bats
#
# Tests for deny-rm.sh, the PreToolUse Bash guard that denies rm and points
# at trash.
#
# The denial cases cover rm at each command position: alone, after each
# separator, in a subshell and a command substitution, behind each wrapper
# word, inside a loop body, in a shell -c string, and behind find -exec.
# The silent cases cover the other programs that spell rm as a subcommand,
# the neighbors trash and rmdir, and the word rm as an argument, inside a
# quoted string, in a comment, and in a here-document body.

setup() {
  export HOME="${BATS_TEST_TMPDIR}/home"
  export XDG_CONFIG_HOME="${HOME}/.config"
  export XDG_DATA_HOME="${HOME}/.local/share"
  export XDG_CACHE_HOME="${HOME}/.cache"
  mkdir -p "${HOME}"
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-rm.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
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
  assert_denies 'sudo rm -rf /var/cache/x'
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
