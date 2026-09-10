#!/usr/bin/env bats
#
# The apiKeyHelper contract, clauses 1 through 5.
#
# The first test is the one that matters most: it installs a helper that
# records having run, then asserts the recording never happened. That is how
# "the plugin never executes a helper" becomes a checkable property rather
# than a stated intention.

# The last test passes a flag to run, which bats guarantees from 1.5.0.
bats_require_minimum_version 1.5.0

setup() {
  load 'helpers/fixture'
  fixture_setup
}

teardown() {
  fixture_teardown
}

# bats test_tags=security
@test "validate never executes the helper it validates" {
  local sentinel="${HARNESS_TEST_DIR}/the-helper-ran"
  local helper
  helper="$(write_tattling_helper "${sentinel}")"
  write_profile tattler <<PROFILE
{
  "schemaVersion": 1,
  "name": "tattler",
  "describe": "Its helper records having run.",
  "settings": {
    "apiKeyHelper": "${helper}",
    "env": { "ANTHROPIC_BASE_URL": "https://example.invalid/anthropic" }
  }
}
PROFILE
  run bash "$(harness_scripts)/harness-profile.sh" validate tattler
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"pass  helper-is-executable"* ]]
  # The helper exists, is executable, and passed every clause the plugin
  # checks. Had anything run it, this file would exist.
  [ ! -f "${sentinel}" ]
}

# bats test_tags=security
@test "use never executes the helper it activates" {
  local sentinel="${HARNESS_TEST_DIR}/the-helper-ran"
  local helper
  helper="$(write_tattling_helper "${sentinel}")"
  write_profile tattler <<PROFILE
{
  "schemaVersion": 1,
  "name": "tattler",
  "describe": "Its helper records having run.",
  "settings": {
    "apiKeyHelper": "${helper}",
    "env": { "ANTHROPIC_BASE_URL": "https://example.invalid/anthropic" }
  }
}
PROFILE
  run bash "$(harness_scripts)/harness-profile.sh" use tattler
  [ "${status}" -eq 0 ]
  [ ! -f "${sentinel}" ]
}

# bats test_tags=security
@test "doctor never executes the active profile's helper" {
  local sentinel="${HARNESS_TEST_DIR}/the-helper-ran"
  local helper
  helper="$(write_tattling_helper "${sentinel}")"
  write_profile tattler <<PROFILE
{
  "schemaVersion": 1,
  "name": "tattler",
  "describe": "Its helper records having run.",
  "settings": {
    "apiKeyHelper": "${helper}",
    "env": { "ANTHROPIC_BASE_URL": "https://example.invalid/anthropic" }
  }
}
PROFILE
  run bash "$(harness_scripts)/harness-profile.sh" use tattler
  [ "${status}" -eq 0 ]
  run bash "$(harness_scripts)/harness-doctor.sh"
  [ ! -f "${sentinel}" ]
}

# bats test_tags=unit
@test "validate reports a missing helper without failing the other gates" {
  write_profile ghost <<'JSON'
{
  "schemaVersion": 1,
  "name": "ghost",
  "describe": "Names a helper nobody installed.",
  "settings": {
    "apiKeyHelper": "/nonexistent/path/to/api-key.sh",
    "env": { "ANTHROPIC_BASE_URL": "https://example.invalid/anthropic" }
  }
}
JSON
  run bash "$(harness_scripts)/harness-profile.sh" validate ghost
  [ "${status}" -eq 5 ]
  [[ "${output}" == *"pass  exempt-bound"* ]]
  [[ "${output}" == *"fail  helper-exists"* ]]
}

# bats test_tags=unit
@test "validate rejects a helper other users can read" {
  local helper="${HARNESS_TEST_DIR}/helper/loose-api-key.sh"
  mkdir -p "${HARNESS_TEST_DIR}/helper"
  printf '#!/bin/bash\nprintf placeholder\n' >"${helper}"
  chmod 755 "${helper}"
  write_profile loose <<PROFILE
{
  "schemaVersion": 1,
  "name": "loose",
  "describe": "Its helper is world readable.",
  "settings": {
    "apiKeyHelper": "${helper}",
    "env": { "ANTHROPIC_BASE_URL": "https://example.invalid/anthropic" }
  }
}
PROFILE
  run bash "$(harness_scripts)/harness-profile.sh" validate loose
  [ "${status}" -eq 5 ]
  [[ "${output}" == *"fail  helper-is-private"* ]]
  [[ "${output}" == *"mode 755"* ]]
}

# bats test_tags=unit
@test "validate rejects a helper that is not executable" {
  local helper="${HARNESS_TEST_DIR}/helper/inert-api-key.sh"
  mkdir -p "${HARNESS_TEST_DIR}/helper"
  printf '#!/bin/bash\nprintf placeholder\n' >"${helper}"
  chmod 600 "${helper}"
  write_profile inert <<PROFILE
{
  "schemaVersion": 1,
  "name": "inert",
  "describe": "Its helper cannot run.",
  "settings": {
    "apiKeyHelper": "${helper}",
    "env": { "ANTHROPIC_BASE_URL": "https://example.invalid/anthropic" }
  }
}
PROFILE
  run bash "$(harness_scripts)/harness-profile.sh" validate inert
  [ "${status}" -eq 5 ]
  [[ "${output}" == *"fail  helper-is-executable"* ]]
}

# bats test_tags=unit
@test "validate rejects a helper sitting inside the plugin" {
  local helper="${HARNESS_PLUGIN_DIR}/templates/api-key-helper.template.sh"
  write_profile inside <<PROFILE
{
  "schemaVersion": 1,
  "name": "inside",
  "describe": "Its helper sits in a tracked tree.",
  "settings": {
    "apiKeyHelper": "${helper}",
    "env": { "ANTHROPIC_BASE_URL": "https://example.invalid/anthropic" }
  }
}
PROFILE
  run bash "$(harness_scripts)/harness-profile.sh" validate inside
  [ "${status}" -eq 5 ]
  [[ "${output}" == *"fail  helper-outside-the-repository"* ]]
}

# bats test_tags=unit
@test "validate passes a profile naming no helper at all" {
  write_profile bare <<'JSON'
{
  "schemaVersion": 1,
  "name": "bare",
  "describe": "Authenticates some other way.",
  "settings": {
    "env": { "ANTHROPIC_BASE_URL": "https://example.invalid/anthropic" }
  }
}
JSON
  run bash "$(harness_scripts)/harness-profile.sh" validate bare
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"pass  helper-not-named"* ]]
}

# bats test_tags=security
@test "the shipped helper template arrives without the executable bit" {
  [ -f "${HARNESS_PLUGIN_DIR}/templates/api-key-helper.template.sh" ]
  [ ! -x "${HARNESS_PLUGIN_DIR}/templates/api-key-helper.template.sh" ]
}

# bats test_tags=security
@test "the shipped helper template fails rather than producing a credential" {
  local copy="${HARNESS_TEST_DIR}/copied-api-key.sh"
  cp "${HARNESS_PLUGIN_DIR}/templates/api-key-helper.template.sh" "${copy}"
  chmod 700 "${copy}"
  # The harness reads stdout as the credential, so stdout is the stream that
  # must be empty. bats merges stderr into $output unless told to separate
  # them, and the template writes its complaint to stderr on purpose.
  run --separate-stderr bash "${copy}"
  [ "${status}" -ne 0 ]
  [ -z "${output}" ]
  [[ "${stderr}" == *"still the unedited template"* ]]
}
