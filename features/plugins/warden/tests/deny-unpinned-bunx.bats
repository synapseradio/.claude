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
# literal text, never its expansion (SC2016). setup sets HOOK and the
# helpers read it, which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-unpinned-bunx.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  isolate_home
}

@test "bunx with a bare package is denied" {
  assert_denies 'bunx cowsay'
}

@test "bunx with a bare package and arguments is denied" {
  assert_denies 'bunx cowsay hello world'
}

@test "bun x with a bare package is denied" {
  assert_denies 'bun x cowsay'
}

@test "bunx with a bare scoped package is denied" {
  assert_denies 'bunx @scope/pkg'
}

@test "bunx with a trailing @ and no version is denied" {
  assert_denies 'bunx cowsay@'
}

@test "bunx with a scoped trailing @ and no version is denied" {
  assert_denies 'bunx @scope/pkg@'
}

@test "bunx with --bun before a bare package is denied" {
  assert_denies 'bunx --bun cowsay'
}

@test "bunx with --silent before a bare package is denied" {
  assert_denies 'bunx --silent cowsay hello'
}

@test "bunx with a value option before a bare package is denied" {
  assert_denies 'bunx --cwd ./app cowsay'
}

@test "bun x with an option before the subcommand is denied" {
  assert_denies 'bun --bun x cowsay'
}

@test "bunx with a bare --package value is denied" {
  assert_denies 'bunx --package typescript tsc --version'
}

@test "bunx with a bare -p value is denied" {
  assert_denies 'bunx -p typescript tsc --version'
}

@test "bunx with a bare --package=value is denied" {
  assert_denies 'bunx --package=typescript tsc'
}

@test "bunx with a pinned binary name but a bare --package is denied" {
  assert_denies 'bunx -p typescript tsc@5.0.0'
}

@test "bunx with one pinned and one bare --package is denied" {
  assert_denies 'bunx -p typescript@5.6.2 -p cowsay tsc'
}

@test "a bare bunx after && is denied" {
  assert_denies 'cd app && bunx cowsay'
}

@test "a bare bunx after a semicolon is denied" {
  assert_denies 'git status; bunx cowsay'
}

@test "a bare bunx after a pipe is denied" {
  assert_denies 'echo hi | bunx cowsay'
}

@test "a bare bunx on a later line is denied" {
  assert_denies $'cd app\nbunx cowsay'
}

@test "a bare bunx inside a subshell is denied" {
  assert_denies '(cd app && bunx cowsay)'
}

@test "a bare bunx inside a command substitution is denied" {
  assert_denies 'echo "$(bunx cowsay)"'
}

@test "a bare bunx behind env is denied" {
  assert_denies 'env CI=1 bunx cowsay'
}

@test "a bare bunx behind xargs is denied" {
  assert_denies 'echo hi | xargs bunx cowsay'
}

@test "a bare bunx in a bash -c string is denied" {
  assert_denies "bash -c 'cd app && bunx cowsay'"
}

@test "a pinned bunx followed by a bare one is denied" {
  assert_denies 'bunx cowsay@1.5.0 && bunx lolcatjs'
}

@test "a bare bunx named by path is denied" {
  assert_denies '/usr/local/bin/bunx cowsay'
}

@test "a denial names the package, the version, and the tool that falls short" {
  run_bash_hook 'bunx cowsay'
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'cowsay'* ]]
  [[ "${reason}" == *'bunx <pkg>@<version>'* ]]
  [[ "${reason}" == *'@latest'* ]]
  [[ "${reason}" == *'the package'* ]]
  [[ "${reason}" == *'the version the command pins'* ]]
  [[ "${reason}" == *'what it executes'* ]]
  [[ "${reason}" == *'which installed tool falls short'* ]]
}

@test "a denial emits a deny and no ask" {
  run_bash_hook 'bunx cowsay'
  [[ "$(jq -r '.hookSpecificOutput.permissionDecision' \
    <<<"${HOOK_OUTPUT}")" == deny ]]
}

@test "bunx with a pinned version is allowed" {
  assert_silent 'bunx cowsay@1.5.0'
}

@test "bunx with the latest tag is allowed" {
  assert_silent 'bunx cowsay@latest'
}

@test "bunx with a scoped package and a version is allowed" {
  assert_silent 'bunx @scope/pkg@2.0.1'
}

@test "bunx with a scoped package and the latest tag is allowed" {
  assert_silent 'bunx @scope/pkg@latest hello'
}

@test "bun x with a pinned version is allowed" {
  assert_silent 'bun x cowsay@1.5.0'
}

@test "bunx with options and a pinned version is allowed" {
  assert_silent 'bunx --bun --silent cowsay@1.5.0 hello'
}

@test "bunx with a value option and a pinned version is allowed" {
  assert_silent 'bunx --cwd ./app cowsay@1.5.0'
}

@test "bunx with a pinned --package value is allowed" {
  assert_silent 'bunx --package typescript@5.6.2 tsc --version'
}

@test "bunx with a pinned -p value is allowed" {
  assert_silent 'bunx -p typescript@5.6.2 tsc --version'
}

@test "bunx with a pinned --package=value is allowed" {
  assert_silent 'bunx --package=typescript@5.6.2 tsc'
}

@test "bunx with a scoped pinned --package value is allowed" {
  assert_silent 'bunx -p @scope/pkg@2.0.1 bin'
}

@test "a bare word after a pinned package is an argument and stays silent" {
  assert_silent 'bunx cowsay@1.5.0 lolcatjs'
}

@test "an option after the package belongs to the package and stays silent" {
  assert_silent 'bunx cowsay@1.5.0 --silent'
}

@test "a pinned bunx in a compound command stays silent" {
  assert_silent 'cd app && bunx cowsay@1.5.0 hello | cat'
}

@test "bunx with no package stays silent" {
  assert_silent 'bunx --version'
}

@test "bare bunx stays silent" {
  assert_silent 'bunx'
}

@test "bun install stays silent" {
  assert_silent 'bun install'
}

@test "bun run stays silent" {
  assert_silent 'bun run x'
}

@test "bun add stays silent" {
  assert_silent 'bun add cowsay'
}

@test "bun create stays silent" {
  assert_silent 'bun create vite my-app'
}

@test "bun with an x argument after another subcommand stays silent" {
  assert_silent 'bun test x'
}

@test "npx stays silent" {
  assert_silent 'npx cowsay'
}

@test "bunx named inside a quoted argument stays silent" {
  assert_silent 'echo "bunx cowsay"'
}

@test "echo bunx stays silent" {
  assert_silent 'echo bunx'
}

@test "bunx as an argument stays silent" {
  assert_silent 'grep -rn bunx scripts/'
}

@test "bunx named inside a commit message stays silent" {
  assert_silent 'git commit -m "docs: explain bun x cowsay"'
}

@test "a word ending in bunx stays silent" {
  assert_silent 'mybunx cowsay'
}

@test "a path containing bunx stays silent" {
  assert_silent 'cat docs/bunx.md'
}

@test "an empty command stays silent" {
  assert_silent ''
}
