#!/usr/bin/env bats
#
# The render entry script refuses what it does not know.

export BATS_TEST_TIMEOUT=10

setup() {
  load '../../tests/test_helper'
  RENDER="${BATS_TEST_DIRNAME}/../../render.sh"
}

@test "render.sh exits 2 and prints usage for an unknown subcommand" {
  setup_sandbox_test_env
  run bash "${RENDER}" frobnicate
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"usage: render.sh render|check|project"* ]]
}

@test "render.sh exits 2 and prints usage when given no subcommand" {
  setup_sandbox_test_env
  run bash "${RENDER}"
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"usage: render.sh render|check|project"* ]]
}
