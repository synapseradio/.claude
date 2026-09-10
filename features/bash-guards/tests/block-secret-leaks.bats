#!/usr/bin/env bats
#
# Tests for block-secret-leaks.sh, the PreToolUse Bash guard that denies a
# command which would print a secret-shaped environment variable.
#
# Each denial case names a command that carries a secret to stdout, and each
# silent case names a command a normal session runs all day. Remove the
# guard's patterns and the denial cases go red.

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/block-secret-leaks.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
}

@test "echo of an API key is denied" {
  assert_denies 'echo $OPENAI_API_KEY'
}

@test "echo of a braced token is denied" {
  assert_denies 'echo "${GITHUB_TOKEN}"'
}

@test "printf of a password is denied" {
  assert_denies 'printf "%s\n" "${DB_PASSWORD}"'
}

@test "a secret behind a parameter expansion modifier is denied" {
  assert_denies 'echo "${AWS_SECRET_ACCESS_KEY:-unset}"'
}

@test "piping a secret into another command is denied" {
  assert_denies 'echo "${SESSION_TOKEN}" | pbcopy'
}

@test "jq interpolating a secret is denied" {
  assert_denies 'jq -nc --arg t "$AUTH_TOKEN" .'
}

@test "printenv is denied" {
  assert_denies 'printenv'
}

@test "printenv narrowed by grep is denied" {
  assert_denies 'printenv | grep -i aws'
}

@test "bare env is denied" {
  assert_denies 'env'
}

@test "bare env piped to a pager is denied" {
  assert_denies 'env | sort'
}

@test "bare set is denied" {
  assert_denies 'set'
}

@test "a denial names the pattern that matched" {
  run_bash_hook 'echo $STRIPE_SECRET_KEY'
  [[ "$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")" == *'secret pattern'* ]]
}

@test "env launching a subprocess stays silent" {
  assert_silent 'env FOO=bar npm test'
}

@test "set with shell options stays silent" {
  assert_silent 'set -euo pipefail'
}

@test "echo of a non-secret variable stays silent" {
  assert_silent 'echo "${PATH}"'
}

@test "echo of a literal string stays silent" {
  assert_silent 'echo "hello world"'
}

@test "an ordinary git command stays silent" {
  assert_silent 'git status --short'
}

@test "reading a source file stays silent" {
  assert_silent 'cat README.md'
}

@test "an empty command stays silent" {
  assert_silent ''
}

@test "env wrapped in nohup is denied" {
  assert_denies 'nohup env'
}

@test "set wrapped in time is denied" {
  assert_denies 'time set'
}

@test "a word ending in env launching a subprocess stays silent" {
  assert_silent 'resend FOO=bar npm test'
}

@test "a word ending in env stays silent" {
  assert_silent 'resend | sort'
}
