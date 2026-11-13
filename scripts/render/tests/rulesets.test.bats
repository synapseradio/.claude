#!/usr/bin/env bats
#
# `render.sh render` and `render.sh check` call the rulesets CLI through its
# launcher. The launcher is a stub that logs its arguments to CALL_LOG.

export BATS_TEST_TIMEOUT=10

setup() {
  load '../../tests/test_helper'
  RENDER="${BATS_TEST_DIRNAME}/../../render.sh"
  CLI='with-python features/plugins/rulesets/lib/rulesets/cli.py'
}

# Start a fixture repository with the stubbed launcher and enter it.
enter_repo() {
  setup_sandbox_test_env
  stub_toolchain
  REPO="${BATS_TEST_TMPDIR}/repo"
  make_fixture_repo "${REPO}"
  stub_rulesets_cli "${REPO}"
  cd "${REPO}" || return 1
}

@test "render renders the rulesets root" {
  enter_repo
  run bash "${RENDER}" render
  [ "${status}" -eq 0 ]
  assert_logged "${CLI} render --root rulesets"
}

@test "render check runs the CLI check, then render --check" {
  enter_repo
  run bash "${RENDER}" check
  [ "${status}" -eq 0 ]
  [ "$(sed -n 1p "${CALL_LOG}")" = "${CLI} check --root rulesets" ]
  [ "$(sed -n 2p "${CALL_LOG}")" = "${CLI} render --check --root rulesets" ]
}

@test "render check exits nonzero when render --check fails" {
  enter_repo
  RULESETS_RENDER_CHECK_STATUS=1 run bash "${RENDER}" check
  [ "${status}" -ne 0 ]
}

@test "render check exits nonzero without running render --check when the CLI check fails" {
  enter_repo
  RULESETS_CHECK_STATUS=1 run bash "${RENDER}" check
  [ "${status}" -ne 0 ]
  refute_logged 'render --check'
}
