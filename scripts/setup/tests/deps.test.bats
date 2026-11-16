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

# Run setup::copy_gauge_types from a plain checkout directory against a primary
# checkout holding 'primary types'. A cp stub records whether the types
# directory exists when the copy starts.
prepare_gauge_types_refresh() {
  setup_sandbox_test_env
  write_gauge_types "${BATS_TEST_TMPDIR}/primary" 'primary types'
  write_gauge_types "${BATS_TEST_TMPDIR}/checkout" 'old types'
  printf 'stale\n' >"${BATS_TEST_TMPDIR}/checkout/${GAUGE_TYPES}/stale.d.ts"
  export PRIMARY_ROOT="${BATS_TEST_TMPDIR}/primary"
  export COPY_PROBE="${BATS_TEST_TMPDIR}/copy-probe.log"
  write_stub cp <<'STUB'
if [[ -d features/mods/context-gauge/.claude-plugin/types ]]; then
  echo present >>"${COPY_PROBE}"
else
  echo missing >>"${COPY_PROBE}"
fi
exec /bin/cp "$@"
STUB
  cd "${BATS_TEST_TMPDIR}/checkout" || return 1
}

GAUGE_TYPES='features/mods/context-gauge/.claude-plugin/types'

refresh_gauge_types() {
  run bash -c 'source "$1" && setup::copy_gauge_types' _ "${BATS_TEST_DIRNAME}/../deps.sh"
}

@test "a gauge types refresh leaves the types directory in place while it copies" {
  prepare_gauge_types_refresh
  refresh_gauge_types
  [ "${status}" -eq 0 ]
  [ -s "${COPY_PROBE}" ]
  run ! grep -qx missing "${COPY_PROBE}"
}

@test "a gauge types refresh over existing types leaves the primary copy and no extra directory" {
  prepare_gauge_types_refresh
  refresh_gauge_types
  [ "${status}" -eq 0 ]
  [ -d "${GAUGE_TYPES}" ]
  [ "$(cat "${GAUGE_TYPES}/tsconfig.json")" = 'primary types' ]
  [ ! -e "${GAUGE_TYPES}/stale.d.ts" ]
  [ "$(ls "${GAUGE_TYPES%/*}")" = 'types' ]
}

@test "a gauge types refresh succeeds after an interrupted run left staging and aside directories" {
  prepare_gauge_types_refresh
  mkdir -p "${GAUGE_TYPES}.staging" "${GAUGE_TYPES}.old"
  printf 'partial\n' >"${GAUGE_TYPES}.staging/partial.d.ts"
  printf 'aside\n' >"${GAUGE_TYPES}.old/aside.d.ts"
  refresh_gauge_types
  [ "${status}" -eq 0 ]
  [ "$(cat "${GAUGE_TYPES}/tsconfig.json")" = 'primary types' ]
  [ "$(ls "${GAUGE_TYPES%/*}")" = 'types' ]
}

@test "a gauge types refresh that fails to copy exits 1 and keeps the existing types" {
  prepare_gauge_types_refresh
  PRIMARY_ROOT="${BATS_TEST_TMPDIR}/missing" refresh_gauge_types
  [ "${status}" -eq 1 ]
  [ "$(cat "${GAUGE_TYPES}/tsconfig.json")" = 'old types' ]
}
