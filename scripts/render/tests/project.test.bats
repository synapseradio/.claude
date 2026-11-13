#!/usr/bin/env bats
#
# `render.sh project` runs the three projection scripts from the primary
# checkout and refuses in a linked worktree, because each script writes under
# the home directory. uv is a stub that logs its calls to CALL_LOG.

export BATS_TEST_TIMEOUT=10

setup() {
  load '../../tests/test_helper'
  RENDER="${BATS_TEST_DIRNAME}/../../render.sh"
  PROJECT='uv run --frozen python scripts/agent-configs'
}

# Start a stubbed primary checkout and enter it.
enter_primary() {
  setup_sandbox_test_env
  stub_toolchain
  PRIMARY="${BATS_TEST_TMPDIR}/primary"
  make_fixture_repo "${PRIMARY}"
  cd "${PRIMARY}" || return 1
}

@test "project exits 2 in a linked worktree and runs nothing" {
  enter_primary
  LINKED="${BATS_TEST_TMPDIR}/linked"
  add_linked_worktree "${PRIMARY}" "${LINKED}"
  cd "${LINKED}"
  run bash "${RENDER}" project --check
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"projections run only from the primary checkout"* ]]
  [ ! -s "${CALL_LOG}" ]
}

@test "project --check runs the three projection scripts with --check" {
  enter_primary
  run bash "${RENDER}" project --check
  [ "${status}" -eq 0 ]
  assert_logged "${PROJECT}/translate-for-pi.py --check"
  assert_logged "${PROJECT}/translate-for-opencode.py --check"
  assert_logged "${PROJECT}/own-opencode-key.py --check"
}

@test "project with no flags runs the three projection scripts bare" {
  enter_primary
  run bash "${RENDER}" project
  [ "${status}" -eq 0 ]
  assert_logged "${PROJECT}/translate-for-pi.py"
  assert_logged "${PROJECT}/translate-for-opencode.py"
  assert_logged "${PROJECT}/own-opencode-key.py"
}

@test "project --agent reaches the two translators and not the key owner" {
  enter_primary
  run bash "${RENDER}" project --agent reviewer
  [ "${status}" -eq 0 ]
  assert_logged "${PROJECT}/translate-for-pi.py --agent reviewer"
  assert_logged "${PROJECT}/translate-for-opencode.py --agent reviewer"
  assert_logged "${PROJECT}/own-opencode-key.py"
}

@test "project stops and exits 1 when a projection script fails" {
  enter_primary
  write_stub uv <<<'exit 1'
  run bash "${RENDER}" project
  [ "${status}" -eq 1 ]
  [ "$(wc -l <"${CALL_LOG}" | tr -d ' ')" -eq 1 ]
}
