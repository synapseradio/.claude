#!/usr/bin/env bats
#
# Tests for ask-shell-c.sh, the PreToolUse Bash hook that prompts when a
# shell runs with -c.
#
# The ask cases cover each shell, -c alone and inside flag clusters, the
# shell behind wrappers and at each command position, and a nested shell.
# The silent cases cover -c on other programs, other interpreters, a shell
# that runs a script file or reads a script from stdin, and the words bash
# and -c inside quotes or as arguments.

setup() {
  export HOME="${BATS_TEST_TMPDIR}/home"
  export XDG_CONFIG_HOME="${HOME}/.config"
  export XDG_DATA_HOME="${HOME}/.local/share"
  export XDG_CACHE_HOME="${HOME}/.cache"
  mkdir -p "${HOME}"
  HOOK="${BATS_TEST_DIRNAME}/../hooks/ask-shell-c.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
}

@test "bash -c asks" {
  assert_asks "bash -c 'echo hi'"
}

@test "sh -c asks" {
  assert_asks "sh -c 'echo hi'"
}

@test "zsh -c asks" {
  assert_asks "zsh -c 'echo hi'"
}

@test "dash -c asks" {
  assert_asks "dash -c 'echo hi'"
}

@test "ksh -c asks" {
  assert_asks "ksh -c 'echo hi'"
}

@test "bash -lc asks" {
  assert_asks "bash -lc 'echo hi'"
}

@test "zsh -ic asks" {
  assert_asks "zsh -ic 'ntn pages list'"
}

@test "bash -xc asks" {
  assert_asks "bash -xc 'echo hi'"
}

@test "bash -c after another option asks" {
  assert_asks "bash -e -c 'echo hi'"
}

@test "bash -o pipefail -c asks" {
  assert_asks "bash -o pipefail -c 'echo hi'"
}

@test "a shell named by path asks" {
  assert_asks "/bin/bash -c 'echo hi'"
}

@test "a shell behind env asks" {
  assert_asks "env FOO=1 bash -c 'echo hi'"
}

@test "a shell behind sudo asks" {
  assert_asks "sudo -u root sh -c 'echo hi'"
}

@test "a shell after && asks" {
  assert_asks "cd build && sh -c 'echo hi'"
}

@test "a shell after a pipe asks" {
  assert_asks "echo hi | sh -c 'cat'"
}

@test "a shell inside a command substitution asks" {
  assert_asks "echo \$(bash -c 'echo hi')"
}

@test "a shell inside a loop body asks" {
  assert_asks "for f in a b; do sh -c 'echo hi'; done"
}

@test "a shell behind find -exec asks" {
  assert_asks "find . -name x -exec sh -c 'echo {}' \\;"
}

@test "a shell nested in a shell -c string asks" {
  assert_asks "bash script.sh && echo ok; bash -c \"zsh -c 'echo hi'\""
}

@test "an ask names the zsh -ic exception and the scratchpad script" {
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
