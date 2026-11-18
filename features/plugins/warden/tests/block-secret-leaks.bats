#!/usr/bin/env bats
#
# Tests for block-secret-leaks.sh, the PreToolUse Bash guard that denies a
# command which would print a secret-shaped environment variable.
#
# Each denial case names a command that carries a secret to stdout, and each
# silent case names a command a normal session runs all day. Remove the
# guard's patterns and the denial cases go red.

# Single quotes are intentional throughout: the guard has to receive the
# literal text, never its expansion (SC2016).
# shellcheck disable=SC2016

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard block-secret-leaks
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

@test "a command that prints a secret-named variable is denied, whatever wraps it" {
  local -a forms=(
    'echo $OPENAI_API_KEY'
    'echo "${GITHUB_TOKEN}"'
    'printf "%s\n" "${DB_PASSWORD}"'
    'echo "${AWS_SECRET_ACCESS_KEY:-unset}"'
    'echo "${SESSION_TOKEN}" | pbcopy'
    'jq -nc --arg t "$AUTH_TOKEN" .'
    "ssh host 'echo \$API_TOKEN'"
    'docker run --rm alpine echo "$API_TOKEN"'
    "bash -c 'echo \$API_TOKEN'"
    "$(nest_in_shell_c 3 'echo $API_TOKEN')"
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "a command that dumps the whole environment is denied, whatever wraps it" {
  local -a forms=(
    'printenv'
    'printenv | grep -i aws'
    'env'
    'env | sort'
    'set'
    'nohup env'
    'time set'
    'FOO=1 env'
    'cd /x && env'
    'env > /tmp/out'
    'echo a; env'
    'echo a; set'
    'cd /x && set | sort'
    'sudo printenv'
    'echo "$(printenv)"'
    "bash -c 'printenv | sort'"
    'timeout 5 printenv'
    'docker exec c printenv'
    'ssh host printenv'
    'timeout 5 env'
    'ssh host env'
    'ssh host env > /tmp/out'
    'grep foo printenv'
    $'bash <<\'EOF\'\nprintenv\nEOF'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "ordinary commands that only resemble a leak stay silent" {
  local -a forms=(
    'env FOO=bar npm test'
    'set -euo pipefail'
    'echo "${PATH}"'
    'echo "hello world"'
    'git status --short'
    'cat README.md'
    ''
    'resend FOO=bar npm test'
    'resend | sort'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "a search that only names a dump word or an echo of a secret stays silent" {
  local -a forms=(
    "rg -n 'git|env|tee' /x"
    'cat f | grep set | head'
    'rg -n printenv /x'
    "rg -n 'echo.*\\\$TOKEN' /x"
    'rg -n -e env -e printenv /x'
    'grep --regexp=printenv /x'
    "grep -rn 'echo \$TOKEN' /x"
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "an envelope proposing printenv prints a PreToolUse denial" {
  assert_main_prints deny \
    '{"tool_name":"Bash","tool_input":{"command":"printenv"}}'
}
