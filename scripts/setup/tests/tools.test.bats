#!/usr/bin/env bats
#
# `setup.sh tools` installs the Brewfile only where `brew bundle check` finds
# something missing. brew is a stub that logs its calls to CALL_LOG.

export BATS_TEST_TIMEOUT=10

setup() {
  load '../../tests/test_helper'
  SETUP="${BATS_TEST_DIRNAME}/../../setup.sh"
}

# Start a stubbed fixture repository and enter it.
enter_repo() {
  setup_sandbox_test_env
  stub_toolchain
  make_fixture_repo "${BATS_TEST_TMPDIR}/repo"
  cd "${BATS_TEST_TMPDIR}/repo" || return 1
}

@test "setup tools installs nothing when the bundle check passes" {
  enter_repo
  BREW_CHECK_STATUS=0 run bash "${SETUP}" tools
  [ "${status}" -eq 0 ]
  assert_logged 'brew bundle check --file Brewfile'
  refute_logged 'brew bundle --file Brewfile'
}

@test "setup tools installs the Brewfile when the bundle check fails" {
  enter_repo
  BREW_CHECK_STATUS=1 run bash "${SETUP}" tools
  [ "${status}" -eq 0 ]
  assert_logged 'brew bundle --file Brewfile'
}
