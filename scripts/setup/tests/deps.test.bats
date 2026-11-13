#!/usr/bin/env bats
#
# `setup.sh deps` provisions a checkout and skips each step whose inputs match
# the stamp its last success left and whose product still exists. bun, uv,
# brew, and claude are stubs that log their calls to CALL_LOG.

export BATS_TEST_TIMEOUT=10

setup() {
  load '../../tests/test_helper'
  SETUP="${BATS_TEST_DIRNAME}/../../setup.sh"
}

# Start a stubbed primary checkout and enter it.
enter_primary() {
  setup_sandbox_test_env
  stub_toolchain
  PRIMARY="${BATS_TEST_TMPDIR}/primary"
  make_fixture_repo "${PRIMARY}"
  cd "${PRIMARY}" || return 1
}

@test "the first setup deps runs bun install and uv sync" {
  enter_primary
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"run bun"* ]]
  [[ "${output}" == *"run uv"* ]]
  assert_logged 'bun install --frozen-lockfile'
  assert_logged 'uv sync --frozen'
}

@test "the second setup deps skips each step and runs no install" {
  enter_primary
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
  enter_primary
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
  enter_primary
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
  enter_primary
  BUN_STATUS=1 run bash "${SETUP}" deps
  [ "${status}" -eq 1 ]
  : >"${CALL_LOG}"
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"run bun"* ]]
  assert_logged 'bun install --frozen-lockfile'
}

@test "the primary checkout skips gauge types and keeps its own copy" {
  enter_primary
  write_gauge_types "${PRIMARY}" 'primary types'
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"skip gauge-types (primary checkout)"* ]]
  [ "$(cat features/mods/context-gauge/.claude-plugin/types/tsconfig.json)" = 'primary types' ]
}

@test "a linked worktree copies gauge types from the primary checkout" {
  enter_primary
  write_gauge_types "${PRIMARY}" 'primary types'
  LINKED="${BATS_TEST_TMPDIR}/linked"
  add_linked_worktree "${PRIMARY}" "${LINKED}"
  cd "${LINKED}"
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"run gauge-types"* ]]
  [ "$(cat features/mods/context-gauge/.claude-plugin/types/tsconfig.json)" = 'primary types' ]
}

@test "a linked worktree skips gauge types on the second run until the primary copy changes" {
  enter_primary
  write_gauge_types "${PRIMARY}" 'primary types'
  LINKED="${BATS_TEST_TMPDIR}/linked"
  add_linked_worktree "${PRIMARY}" "${LINKED}"
  cd "${LINKED}"
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"skip gauge-types (inputs unchanged)"* ]]
  write_gauge_types "${PRIMARY}" 'newer types'
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"run gauge-types"* ]]
  [ "$(cat features/mods/context-gauge/.claude-plugin/types/tsconfig.json)" = 'newer types' ]
}

@test "a linked worktree skips gauge types when the primary checkout has none" {
  enter_primary
  LINKED="${BATS_TEST_TMPDIR}/linked"
  add_linked_worktree "${PRIMARY}" "${LINKED}"
  cd "${LINKED}"
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"skip gauge-types (no types in the primary checkout)"* ]]
}

@test "stamps live under .cache/verify in the checkout" {
  enter_primary
  run bash "${SETUP}" deps
  [ "${status}" -eq 0 ]
  [ -d .cache/verify ]
  [ -n "$(ls .cache/verify)" ]
}
