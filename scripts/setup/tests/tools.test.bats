#!/usr/bin/env bats
#
# `setup.sh tools` installs the Brewfile only where `brew bundle check` finds
# something missing. brew is a stub that logs its calls to CALL_LOG.

export BATS_TEST_TIMEOUT=10

setup_file() {
  load '../../tests/test_helper'
  build_fixture_repo_once
}

setup() {
  load '../../tests/test_helper'
  SETUP="${BATS_TEST_DIRNAME}/../../setup.sh"
}

@test "setup tools installs nothing when the bundle check passes" {
  enter_fixture_repo repo
  BREW_CHECK_STATUS=0 run bash "${SETUP}" tools
  [ "${status}" -eq 0 ]
  assert_logged 'brew bundle check --file Brewfile'
  refute_logged 'brew bundle --file Brewfile'
}

@test "setup tools installs the Brewfile when the bundle check fails" {
  enter_fixture_repo repo
  BREW_CHECK_STATUS=1 run bash "${SETUP}" tools
  [ "${status}" -eq 0 ]
  assert_logged 'brew bundle --file Brewfile'
}
