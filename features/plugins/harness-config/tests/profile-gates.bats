#!/usr/bin/env bats
#
# The two gates a profile passes before activation.
#
# Expected results come from docs/design.md's contract table rather than from
# the gate code, so a gate that agrees with itself still fails these.

setup() {
  load 'helpers/fixture'
  fixture_setup
}

teardown() {
  fixture_teardown
}

# bats test_tags=unit
@test "validate accepts a profile declaring only exempt paths" {
  write_valid_profile good
  run bash "$(harness_scripts)/harness-profile.sh" validate good
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"pass  shape"* ]]
  [[ "${output}" == *"pass  exempt-bound"* ]]
  [[ "${output}" == *"pass  credential-guard"* ]]
}

# bats test_tags=unit
@test "validate rejects a profile declaring a path outside the exempt list" {
  write_profile policy <<'JSON'
{
  "schemaVersion": 1,
  "name": "policy",
  "describe": "Reaches for policy the floor owns.",
  "settings": { "permissions": { "allow": ["Bash(rm -rf /*)"] } }
}
JSON
  run bash "$(harness_scripts)/harness-profile.sh" validate policy
  [ "${status}" -eq 5 ]
  [[ "${output}" == *"fail  exempt-bound"* ]]
  [[ "${output}" == *"permissions.allow"* ]]
}

# bats test_tags=unit
@test "validate rejects a credential-named path the exempt list permits" {
  write_profile inline <<'JSON'
{
  "schemaVersion": 1,
  "name": "inline",
  "describe": "Puts a token where the registry exempts one.",
  "settings": { "env": { "ANTHROPIC_AUTH_TOKEN": "placeholder-value" } }
}
JSON
  run bash "$(harness_scripts)/harness-profile.sh" validate inline
  # The exempt bound admits this path, so the credential guard is the only
  # thing standing between a token and a profile file. This test is what
  # proves the two gates do not subsume each other.
  [ "${status}" -eq 5 ]
  [[ "${output}" == *"pass  exempt-bound"* ]]
  [[ "${output}" == *"fail  credential-guard"* ]]
  [[ "${output}" == *"env.ANTHROPIC_AUTH_TOKEN"* ]]
}

#######################################
# Assemble a credential-shaped string from two halves, so this test file
# carries no credential shape for harness-guard.sh material to find. A test
# that plants the shape it tests for would fail the plugin's own scan.
# Outputs:
#   The assembled string on STDOUT.
#######################################
shaped_value() {
  printf '%s%s\n' 'sk-' 'abcdefghijklmnopqrstuvwx'
}

# bats test_tags=unit
@test "validate rejects a credential-shaped value at a path with an innocent name" {
  local shaped
  shaped="$(shaped_value)"
  write_profile shaped <<PROFILE
{
  "schemaVersion": 1,
  "name": "shaped",
  "describe": "A credential shape at a name the guard would not flag.",
  "settings": { "env": { "ANTHROPIC_BASE_URL": "${shaped}" } }
}
PROFILE
  run bash "$(harness_scripts)/harness-profile.sh" validate shaped
  [ "${status}" -eq 5 ]
  [[ "${output}" == *"fail  credential-guard"* ]]
  [[ "${output}" == *"no-credential-shaped-value"* ]]
}

# bats test_tags=unit
@test "validate output withholds the credential-shaped value it rejected" {
  local shaped
  shaped="$(shaped_value)"
  write_profile shaped <<PROFILE
{
  "schemaVersion": 1,
  "name": "shaped",
  "describe": "A credential shape the report must not echo.",
  "settings": { "env": { "ANTHROPIC_BASE_URL": "${shaped}" } }
}
PROFILE
  run bash "$(harness_scripts)/harness-profile.sh" validate shaped
  [ "${status}" -eq 5 ]
  # The report names the path and never the value, which is the property that
  # keeps a rejection from publishing what it rejected.
  [[ "${output}" != *"${shaped}"* ]]
}

# bats test_tags=unit
@test "validate rejects a profile whose schemaVersion is not 1" {
  write_profile future <<'JSON'
{
  "schemaVersion": 2,
  "name": "future",
  "describe": "A version this reader does not know.",
  "settings": { "env": { "ANTHROPIC_BASE_URL": "https://example.invalid" } }
}
JSON
  run bash "$(harness_scripts)/harness-profile.sh" validate future
  [ "${status}" -eq 5 ]
  [[ "${output}" == *"fail  shape"* ]]
  [[ "${output}" == *"schema-version-is-1"* ]]
}

# bats test_tags=unit
@test "add rejects a profile name that would escape the profiles directory" {
  run bash "$(harness_scripts)/harness-profile.sh" add ../escape
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"a profile name matches"* ]]
}

# bats test_tags=unit
@test "add rejects the reserved name base" {
  run bash "$(harness_scripts)/harness-profile.sh" add base
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"names a settings file that is not a variant"* ]]
}

# bats test_tags=unit
@test "show withholds a value at a credential-named path" {
  write_profile inline <<'JSON'
{
  "schemaVersion": 1,
  "name": "inline",
  "describe": "Holds a token, so show must withhold it.",
  "settings": { "env": { "ANTHROPIC_AUTH_TOKEN": "placeholder-value" } }
}
JSON
  run bash "$(harness_scripts)/harness-profile.sh" show inline
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"env.ANTHROPIC_AUTH_TOKEN = <withheld>"* ]]
  [[ "${output}" != *"placeholder-value"* ]]
}
