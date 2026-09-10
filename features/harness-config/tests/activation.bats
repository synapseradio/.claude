#!/usr/bin/env bats
#
# Activation writes the paths a profile declares and nothing else.
#
# The expected results come from docs/design.md's statement that the write is
# bounded, so a test here fails whenever activation grows a side effect.

setup() {
  load 'helpers/fixture'
  fixture_setup
}

teardown() {
  fixture_teardown
}

# bats test_tags=integration
@test "use writes every path the profile declares into settings.json" {
  write_valid_profile good
  run bash "$(harness_scripts)/harness-profile.sh" use good
  [ "${status}" -eq 0 ]
  run jq -r '.env.ANTHROPIC_BASE_URL' "${CLAUDE_CONFIG_DIR}/settings.json"
  [ "${output}" = "https://gateway.example.invalid/anthropic" ]
  run jq -r '.env.ANTHROPIC_DEFAULT_OPUS_MODEL' "${CLAUDE_CONFIG_DIR}/settings.json"
  [ "${output}" = "example-large" ]
}

# bats test_tags=integration
@test "use leaves a key the profile does not declare exactly as it was" {
  cat >"${CLAUDE_CONFIG_DIR}/settings.json" <<'JSON'
{ "theme": "dark", "env": { "SOMETHING_ELSE": "kept" } }
JSON
  write_valid_profile good
  run bash "$(harness_scripts)/harness-profile.sh" use good
  [ "${status}" -eq 0 ]
  # A file swap would drop both of these. A bounded write keeps them, which is
  # what makes /config's own writes survive a profile switch.
  run jq -r '.theme' "${CLAUDE_CONFIG_DIR}/settings.json"
  [ "${output}" = "dark" ]
  run jq -r '.env.SOMETHING_ELSE' "${CLAUDE_CONFIG_DIR}/settings.json"
  [ "${output}" = "kept" ]
}

# bats test_tags=integration
@test "use records the active profile in the pointer outside every settings file" {
  write_valid_profile good
  run bash "$(harness_scripts)/harness-profile.sh" use good
  [ "${status}" -eq 0 ]
  run cat "${HARNESS_CONFIG_DATA}/active"
  [ "${output}" = "good" ]
  # The pointer is deliberately absent from settings.json: a settings key
  # naming the active profile would be a path the profile itself owns.
  run jq -r 'paths(scalars) | join(".")' "${CLAUDE_CONFIG_DIR}/settings.json"
  [[ "${output}" != *"activeProfile"* ]]
}

# bats test_tags=integration
@test "use copies the previous settings.json aside before writing" {
  cat >"${CLAUDE_CONFIG_DIR}/settings.json" <<'JSON'
{ "theme": "light" }
JSON
  write_valid_profile good
  run bash "$(harness_scripts)/harness-profile.sh" use good
  [ "${status}" -eq 0 ]
  run bash -c "ls '${HARNESS_CONFIG_DATA}/backups' | wc -l"
  [ "${output// /}" = "1" ]
}

# bats test_tags=integration
@test "use writes nothing when the profile fails a gate" {
  cat >"${CLAUDE_CONFIG_DIR}/settings.json" <<'JSON'
{ "theme": "untouched" }
JSON
  write_profile bad <<'JSON'
{
  "schemaVersion": 1,
  "name": "bad",
  "describe": "Reaches for policy.",
  "settings": { "permissions": { "allow": ["Bash(rm -rf /*)"] } }
}
JSON
  run bash "$(harness_scripts)/harness-profile.sh" use bad
  [ "${status}" -eq 5 ]
  run jq -r 'paths(scalars) | join(".")' "${CLAUDE_CONFIG_DIR}/settings.json"
  [ "${output}" = "theme" ]
  [ ! -f "${HARNESS_CONFIG_DATA}/active" ]
}

# bats test_tags=integration
@test "use switches back by rewriting the same declared paths" {
  write_valid_profile first
  write_profile second <<'JSON'
{
  "schemaVersion": 1,
  "name": "second",
  "describe": "A second provider.",
  "settings": {
    "env": {
      "ANTHROPIC_BASE_URL": "https://other.example.invalid/anthropic",
      "ANTHROPIC_DEFAULT_OPUS_MODEL": "other-large",
      "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "Other Large"
    }
  }
}
JSON
  run bash "$(harness_scripts)/harness-profile.sh" use first
  [ "${status}" -eq 0 ]
  run bash "$(harness_scripts)/harness-profile.sh" use second
  [ "${status}" -eq 0 ]
  run jq -r '.env.ANTHROPIC_BASE_URL' "${CLAUDE_CONFIG_DIR}/settings.json"
  [ "${output}" = "https://other.example.invalid/anthropic" ]
  run bash "$(harness_scripts)/harness-profile.sh" current
  [ "${output}" = "second" ]
}

# bats test_tags=integration
@test "doctor reports the active profile fully in effect after use" {
  write_valid_profile good
  run bash "$(harness_scripts)/harness-profile.sh" use good
  [ "${status}" -eq 0 ]
  run bash "$(harness_scripts)/harness-doctor.sh"
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"pass  declared-paths-present"* ]]
  [[ "${output}" == *"fully in effect"* ]]
}

# bats test_tags=integration
@test "doctor reports a stale value without printing either value" {
  write_valid_profile good
  run bash "$(harness_scripts)/harness-profile.sh" use good
  [ "${status}" -eq 0 ]
  # Simulate a hand edit that drifted from the profile.
  run bash -c "jq '.env.ANTHROPIC_BASE_URL = \"https://drifted.example.invalid\"' '${CLAUDE_CONFIG_DIR}/settings.json' > '${CLAUDE_CONFIG_DIR}/s.tmp'"
  mv "${CLAUDE_CONFIG_DIR}/s.tmp" "${CLAUDE_CONFIG_DIR}/settings.json"
  run bash "$(harness_scripts)/harness-doctor.sh"
  [ "${status}" -eq 7 ]
  [[ "${output}" == *"fail  value-matches"* ]]
  [[ "${output}" == *"env.ANTHROPIC_BASE_URL"* ]]
  # Neither the profile's value nor the drifted one appears; the report
  # compares digests, so it names the path and shows two short hashes.
  [[ "${output}" != *"gateway.example.invalid"* ]]
  [[ "${output}" != *"drifted.example.invalid"* ]]
}

# bats test_tags=integration
@test "doctor reports no active profile when the pointer is missing" {
  cat >"${CLAUDE_CONFIG_DIR}/settings.json" <<'JSON'
{ "theme": "dark" }
JSON
  run bash "$(harness_scripts)/harness-doctor.sh"
  [ "${status}" -eq 7 ]
  [[ "${output}" == *"fail  a-profile-is-active"* ]]
}
