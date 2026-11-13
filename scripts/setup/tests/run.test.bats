#!/usr/bin/env bats
#
# The setup entry script refuses what it does not know.

export BATS_TEST_TIMEOUT=10

setup() {
  load '../../tests/test_helper'
  SETUP="${BATS_TEST_DIRNAME}/../../setup.sh"
}

@test "setup.sh exits 2 and prints usage for an unknown subcommand" {
  setup_sandbox_test_env
  run bash "${SETUP}" frobnicate
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"usage: setup.sh deps|tools"* ]]
}

@test "setup.sh exits 2 and prints usage when given no subcommand" {
  setup_sandbox_test_env
  run bash "${SETUP}"
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"usage: setup.sh deps|tools"* ]]
}
