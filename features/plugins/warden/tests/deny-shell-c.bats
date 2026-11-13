#!/usr/bin/env bats
#
# Tests for deny-shell-c.sh, the PreToolUse Bash hook that refuses a shell
# run with -c, and prompts for an interactive zsh -c.
#
# The deny cases cover each shell, -c alone and inside flag clusters, the
# shell behind wrappers and at each command position, and a nested shell.
# The ask cases cover zsh with -i and -c, the one form a CLI whose
# credentials load only in an interactive shell needs. The silent cases
# cover -c on other programs, other interpreters, a shell that runs a script
# file or reads a script from stdin, and the words bash and -c inside quotes
# or as arguments.
#
# setup sets HOOK and the helpers read it, which shellcheck cannot see.
# shellcheck disable=SC2034

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-shell-c.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  isolate_home
}

@test "bash -c is denied" {
  assert_denies "bash -c 'echo hi'"
}

@test "sh -c is denied" {
  assert_denies "sh -c 'echo hi'"
}

@test "zsh -c is denied" {
  assert_denies "zsh -c 'echo hi'"
}

@test "dash -c is denied" {
  assert_denies "dash -c 'echo hi'"
}

@test "ksh -c is denied" {
  assert_denies "ksh -c 'echo hi'"
}

@test "bash -lc is denied" {
  assert_denies "bash -lc 'echo hi'"
}

@test "zsh -ic asks, for a CLI whose credentials load only interactively" {
  assert_asks "zsh -ic 'ntn pages list'"
}

@test "zsh -i -c asks" {
  assert_asks "zsh -i -c 'spu'"
}

@test "bash -ic is denied" {
  assert_denies "bash -ic 'echo hi'"
}

@test "zsh -c without -i is denied" {
  assert_denies "zsh -l -c 'echo hi'"
}

@test "bash -xc is denied" {
  assert_denies "bash -xc 'echo hi'"
}

@test "bash -c after another option is denied" {
  assert_denies "bash -e -c 'echo hi'"
}

@test "bash -o pipefail -c is denied" {
  assert_denies "bash -o pipefail -c 'echo hi'"
}

@test "a shell named by path is denied" {
  assert_denies "/bin/bash -c 'echo hi'"
}

@test "a shell behind env is denied" {
  assert_denies "env FOO=1 bash -c 'echo hi'"
}

@test "a shell behind sudo is denied" {
  assert_denies "sudo -u root sh -c 'echo hi'"
}

@test "a shell after && is denied" {
  assert_denies "cd build && sh -c 'echo hi'"
}

@test "a shell after a pipe is denied" {
  assert_denies "echo hi | sh -c 'cat'"
}

@test "a shell inside a command substitution is denied" {
  assert_denies "echo \$(bash -c 'echo hi')"
}

@test "a shell inside a loop body is denied" {
  assert_denies "for f in a b; do sh -c 'echo hi'; done"
}

@test "a shell behind find -exec is denied" {
  assert_denies "find . -name x -exec sh -c 'echo {}' \\;"
}

@test "a shell nested in a shell -c string is denied" {
  assert_denies "bash script.sh && echo ok; bash -c \"zsh -c 'echo hi'\""
}

@test "a denial names the zsh -ic exception and the scratchpad script" {
  run_bash_hook "bash -c 'echo hi'"
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *"zsh -ic '<command>'"* ]]
  [[ "${reason}" == *'script file in the scratchpad'* ]]
}

@test "grep -c stays silent" {
  assert_silent 'grep -c needle file'
}

@test "git commit -c stays silent" {
  assert_silent 'git commit -c HEAD'
}

@test "python3 -c stays silent" {
  assert_silent "python3 -c 'print(1)'"
}

@test "node -e stays silent" {
  assert_silent "node -e 'console.log(1)'"
}

@test "a shell running a script file stays silent" {
  assert_silent 'bash script.sh'
}

@test "a script file's own -c argument stays silent" {
  assert_silent 'bash script.sh -c config.yml'
}

@test "a shell with only non-c options stays silent" {
  assert_silent 'bash -e -x script.sh'
}

@test "bash --version stays silent" {
  assert_silent 'bash --version'
}

@test "a shell reading stdin stays silent" {
  assert_silent 'bash -s < script.sh'
}

@test "bash -c as an argument to echo stays silent" {
  assert_silent 'echo bash -c'
}

@test "bash -c inside a double-quoted string stays silent" {
  assert_silent 'echo "run bash -c later"'
}

@test "bash -c in a commit message stays silent" {
  assert_silent 'git commit -m "docs: explain bash -c"'
}

@test "bash -c in a comment stays silent" {
  assert_silent $'ls # bash -c x\npwd'
}

@test "bash -c at the start of a here-document line stays silent" {
  assert_silent $'cat <<\'EOF\'\nbash -c ls\nEOF'
}

@test "a file named bash stays silent" {
  assert_silent 'cat docs/bash.md'
}

@test "an empty command stays silent" {
  assert_silent ''
}
