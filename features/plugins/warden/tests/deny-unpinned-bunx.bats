#!/usr/bin/env bats
#
# Tests for deny-unpinned-bunx.sh, the PreToolUse Bash hook that denies a
# bunx or bun x command whose package argument names no version.
#
# The denial cases cover a bare package, a scoped package, the options bunx
# takes ahead of the package, --package, and each command position the match
# may sit at. The silent cases cover a version, a tag, a scoped version, and
# the neighbors that run nothing fetched.

# Single quotes are intentional throughout: the guard has to receive the
# literal text, never its expansion (SC2016).
# shellcheck disable=SC2016

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard deny-unpinned-bunx
  isolate_home
}

@test "bunx or bun x with a bare package is denied in each argument form" {
  local -a forms=(
    'bunx cowsay'
    'bunx cowsay hello world'
    'bun x cowsay'
    'bunx @scope/pkg'
    'bunx cowsay@'
    'bunx @scope/pkg@'
    'bunx --bun cowsay'
    'bunx --silent cowsay hello'
    'bunx --cwd ./app cowsay'
    'bun --bun x cowsay'
    'bunx --package typescript tsc --version'
    'bunx -p typescript tsc --version'
    'bunx --package=typescript tsc'
    'bunx -p typescript tsc@5.0.0'
    'bunx -p typescript@5.6.2 -p cowsay tsc'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "a bare bunx is denied at each command position" {
  local -a forms=(
    'cd app && bunx cowsay'
    'git status; bunx cowsay'
    'echo hi | bunx cowsay'
    $'cd app\nbunx cowsay'
    '(cd app && bunx cowsay)'
    'echo "$(bunx cowsay)"'
    'env CI=1 bunx cowsay'
    'echo hi | xargs bunx cowsay'
    "bash -c 'cd app && bunx cowsay'"
    'bunx cowsay@1.5.0 && bunx lolcatjs'
    '${DOTTY_LOCAL_PREFIX:-/usr/local}/bin/bunx cowsay'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "bunx with every package pinned stays silent in each argument form" {
  local -a forms=(
    'bunx cowsay@1.5.0'
    'bunx cowsay@latest'
    'bunx @scope/pkg@2.0.1'
    'bunx @scope/pkg@latest hello'
    'bun x cowsay@1.5.0'
    'bunx --bun --silent cowsay@1.5.0 hello'
    'bunx --cwd ./app cowsay@1.5.0'
    'bunx --package typescript@5.6.2 tsc --version'
    'bunx -p typescript@5.6.2 tsc --version'
    'bunx --package=typescript@5.6.2 tsc'
    'bunx -p @scope/pkg@2.0.1 bin'
    'bunx cowsay@1.5.0 lolcatjs'
    'bunx cowsay@1.5.0 --silent'
    'cd app && bunx cowsay@1.5.0 hello | cat'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "bunx without a package, other commands, and bunx named as text stay silent" {
  local -a forms=(
    'bunx --version'
    'bunx'
    'bun install'
    'bun run x'
    'bun add cowsay'
    'bun create vite my-app'
    'bun test x'
    'npx cowsay'
    'echo "bunx cowsay"'
    'echo bunx'
    'grep -rn bunx scripts/'
    'git commit -m "docs: explain bun x cowsay"'
    'mybunx cowsay'
    'cat docs/bunx.md'
    ''
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "an envelope proposing an unpinned bunx prints a PreToolUse denial" {
  assert_main_prints deny \
    '{"tool_name":"Bash","tool_input":{"command":"bunx cowsay"}}'
}
