#!/usr/bin/env bats
#
# `setup.sh deps` provisions a checkout and skips each step whose inputs match
# the stamp its last success left and whose product still exists. bun, uv,
# brew, and claude are stubs that log their calls to CALL_LOG.

export BATS_TEST_TIMEOUT=10

setup_file() {
  load '../../tests/test_helper'
  build_fixture_repo_once
}

setup() {
  load '../../tests/test_helper'
  SETUP="${BATS_TEST_DIRNAME}/../../setup.sh"
}

@test "the first setup deps runs bun install and uv sync" {
  enter_fixture_repo primary
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"run bun"* ]]
  [[ "${output}" == *"run uv"* ]]
  assert_logged 'bun install --frozen-lockfile'
  assert_logged 'uv sync --frozen'
}

@test "the second setup deps skips each step and runs no install" {
  enter_fixture_repo primary
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  : >"${CALL_LOG}"
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"skip bun (inputs unchanged)"* ]]
  [[ "${output}" == *"skip uv (inputs unchanged)"* ]]
  [ ! -s "${CALL_LOG}" ]
}

@test "a changed bun.lock reruns bun and skips uv" {
  enter_fixture_repo primary
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  : >"${CALL_LOG}"
  printf 'lock 2\n' >bun.lock
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"run bun"* ]]
  [[ "${output}" == *"skip uv (inputs unchanged)"* ]]
  assert_logged 'bun install --frozen-lockfile'
  refute_logged 'uv sync'
}

@test "a missing node_modules/.bin/biome reruns bun" {
  enter_fixture_repo primary
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  : >"${CALL_LOG}"
  rm node_modules/.bin/biome
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"run bun"* ]]
  assert_logged 'bun install --frozen-lockfile'
  [ -e node_modules/.bin/biome ]
}

@test "a failed bun install exits 1 and leaves no stamp, so the next run installs" {
  enter_fixture_repo primary
  BUN_STATUS=1 run bash "${SETUP}" deps
  [ "${status}" -eq 1 ]
  : >"${CALL_LOG}"
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"run bun"* ]]
  assert_logged 'bun install --frozen-lockfile'
}

@test "the primary checkout skips gauge types and keeps its own copy" {
  enter_fixture_repo primary
  write_gauge_types "${BATS_TEST_TMPDIR}/primary" 'primary types'
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"skip gauge-types (primary checkout)"* ]]
  [ "$(cat features/mods/context-gauge/.claude-plugin/types/tsconfig.json)" = 'primary types' ]
}

@test "a linked worktree copies gauge types from the primary checkout" {
  enter_fixture_repo primary
  write_gauge_types "${BATS_TEST_TMPDIR}/primary" 'primary types'
  enter_linked_worktree
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"run gauge-types"* ]]
  [ "$(cat features/mods/context-gauge/.claude-plugin/types/tsconfig.json)" = 'primary types' ]
}

@test "a linked worktree skips gauge types on the second run until the primary copy changes" {
  enter_fixture_repo primary
  write_gauge_types "${BATS_TEST_TMPDIR}/primary" 'primary types'
  enter_linked_worktree
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"skip gauge-types (inputs unchanged)"* ]]
  write_gauge_types "${BATS_TEST_TMPDIR}/primary" 'newer types'
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"run gauge-types"* ]]
  [ "$(cat features/mods/context-gauge/.claude-plugin/types/tsconfig.json)" = 'newer types' ]
}

@test "a linked worktree skips gauge types when the primary checkout has none" {
  enter_fixture_repo primary
  enter_linked_worktree
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"skip gauge-types (no types in the primary checkout)"* ]]
}

@test "stamps live under .cache/verify in the checkout" {
  enter_fixture_repo primary
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [ -d .cache/verify ]
  [ -n "$(ls .cache/verify)" ]
}
