#!/usr/bin/env bats
#
# Tests for block-secret-leaks.sh, the PreToolUse Bash guard that denies a
# command which would print a secret-shaped environment variable.
#
# Each denial case names a command that carries a secret to stdout, and each
# silent case names a command a normal session runs all day. Remove the
# guard's patterns and the denial cases go red.

# Single quotes are intentional throughout: the guard has to receive the
# literal text, never its expansion (SC2016). setup sets HOOK and the
# helpers read it, which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/block-secret-leaks.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  isolate_home
}

#######################################
# Wrap a command in a single-quoted bash -c string, once per level, with each
# inner quote escaped so a real shell runs the result.
# Arguments:
#   $1 - how many bash -c strings to nest.
#   $2 - the innermost command.
# Outputs:
#   The nested command text on stdout.
#######################################
nest_in_shell_c() {
  local levels="$1" command="$2" level
  local quote="'" escaped="'\\''"
  for ((level = 0; level < levels; level++)); do
    command="bash -c '${command//${quote}/${escaped}}'"
  done
  printf '%s' "${command}"
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

@test "a search for the word env inside a quoted pattern stays silent" {
  assert_silent "rg -n 'git|env|tee' /x"
}

@test "a search for the word set after a pipe stays silent" {
  assert_silent 'cat f | grep set | head'
}

@test "a search for the word printenv stays silent" {
  assert_silent 'rg -n printenv /x'
}

@test "a search pattern that spells an echo of a secret stays silent" {
  assert_silent "rg -n 'echo.*\\\$TOKEN' /x"
}

@test "bare env behind an assignment, a separator, or a redirect is denied" {
  assert_denies 'FOO=1 env'
  assert_denies 'cd /x && env'
  assert_denies 'env > /tmp/out'
  assert_denies 'echo a; env'
}

@test "bare set behind a separator is denied" {
  assert_denies 'echo a; set'
  assert_denies 'cd /x && set | sort'
}

@test "printenv behind a wrapper, a substitution, or a shell string is denied" {
  assert_denies 'sudo printenv'
  assert_denies 'echo "$(printenv)"'
  assert_denies "bash -c 'printenv | sort'"
}

@test "printenv handed to a launcher the resolver does not unwrap is denied" {
  assert_denies 'timeout 5 printenv'
  assert_denies 'docker exec c printenv'
  assert_denies 'ssh host printenv'
}

@test "bare env handed to a launcher the resolver does not unwrap is denied" {
  assert_denies 'timeout 5 env'
  assert_denies 'ssh host env'
  assert_denies 'ssh host env > /tmp/out'
}

@test "an echo of a secret inside a quoted remote command is denied" {
  assert_denies "ssh host 'echo \$API_TOKEN'"
}

@test "a pattern given with -e to grep or rg stays silent for each dump word" {
  assert_silent 'rg -n -e env -e printenv /x'
  assert_silent 'grep --regexp=printenv /x'
  assert_silent "grep -rn 'echo \$TOKEN' /x"
}

@test "a file named after the pattern of grep is still checked for a dump word" {
  assert_denies 'grep foo printenv'
}

@test "an echo of a secret handed to another launcher is denied" {
  assert_denies 'docker run --rm alpine echo "$API_TOKEN"'
  assert_denies "bash -c 'echo \$API_TOKEN'"
}

@test "a secret printed inside a bash -c string nested three levels deep is denied" {
  assert_denies "$(nest_in_shell_c 3 'echo $API_TOKEN')"
}

@test "a here-document run by a shell that dumps the environment is denied" {
  assert_denies $'bash <<\'EOF\'\nprintenv\nEOF'
}
