# shellcheck shell=bash
#
# Fixture builder for the harness-config suite.
#
# Every test gets its own temporary directory and points the scripts at it
# through the two override variables the scripts resolve first. A script under
# test therefore has no path to real user state, so no test can read the
# user's settings even by mistake.
#
# The synthetic settings.base.json below is written here, in this file, and
# never copied from the machine. Its alignment.exempt list mirrors the shape
# of a real one, which is what the exempt-bound gate reads.

# The directory holding the scripts under test.
harness_scripts() {
  printf '%s/scripts\n' "${HARNESS_PLUGIN_DIR}"
}

#######################################
# Create a temporary config root and data root, and export the overrides.
# Every test calls this in setup.
# Globals:
#   Sets HARNESS_TEST_DIR, CLAUDE_CONFIG_DIR, HARNESS_CONFIG_DATA,
#   HARNESS_PLUGIN_DIR.
#######################################
fixture_setup() {
  HARNESS_PLUGIN_DIR="$(cd -- "${BATS_TEST_DIRNAME}/.." && pwd)"
  HARNESS_TEST_DIR="$(mktemp -d "${BATS_TMPDIR:-/tmp}/harness-config.XXXXXX")"
  export HARNESS_PLUGIN_DIR HARNESS_TEST_DIR
  export CLAUDE_CONFIG_DIR="${HARNESS_TEST_DIR}/config"
  export HARNESS_CONFIG_DATA="${HARNESS_TEST_DIR}/data"
  export CLAUDE_PLUGIN_ROOT="${HARNESS_PLUGIN_DIR}"
  mkdir -p "${CLAUDE_CONFIG_DIR}" "${HARNESS_CONFIG_DATA}/profiles"
  write_base
}

#######################################
# Remove the temporary directory through the variable that created it, never
# through a resolved path a typo could turn into something real.
#######################################
fixture_teardown() {
  if [[ -n "${HARNESS_TEST_DIR:-}" && -d "${HARNESS_TEST_DIR}" ]]; then
    rm -rf "${HARNESS_TEST_DIR}"
  fi
}

#######################################
# Write a synthetic policy floor. Exempts the four path patterns a real one
# exempts, so the exempt-bound gate has something to bound against.
#######################################
write_base() {
  cat >"${CLAUDE_CONFIG_DIR}/settings.base.json" <<'BASE'
{
  "alignment": {
    "exempt": [
      { "path": "apiKeyHelper", "why": "Names this profile's key command." },
      { "path": "env.ANTHROPIC_AUTH_TOKEN", "why": "A live credential." },
      { "path": "env.ANTHROPIC_BASE_URL", "why": "One provider endpoint." },
      { "path": "env.ANTHROPIC_DEFAULT_*", "why": "Per-provider model pins." }
    ],
    "notAVariant": ["settings.local.json"],
    "keyed": { "hooks.*": "matcher", "hooks.*.hooks": "hookPayload" }
  },
  "env": { "CLAUDE_CODE_ENABLE_TELEMETRY": "1" },
  "permissions": { "allow": ["Bash(jq:*)"], "ask": [], "deny": [] }
}
BASE
}

#######################################
# Write a profile file directly, bypassing the add command, so a test can
# construct an illegal profile the add command would not produce.
# Arguments:
#   $1: the profile name.
#   stdin: the profile JSON.
#######################################
write_profile() {
  local name="$1"
  cat >"${HARNESS_CONFIG_DATA}/profiles/${name}.json"
}

#######################################
# Write a valid profile naming a helper this function also installs.
# Arguments:
#   $1: the profile name.
#######################################
write_valid_profile() {
  local name="$1"
  local helper="${HARNESS_TEST_DIR}/helper/api-key.sh"
  mkdir -p "${HARNESS_TEST_DIR}/helper"
  cat >"${helper}" <<'HELPER'
#!/bin/bash
printf 'placeholder-not-a-real-credential'
HELPER
  chmod 700 "${helper}"
  write_profile "${name}" <<PROFILE
{
  "schemaVersion": 1,
  "name": "${name}",
  "describe": "A synthetic profile built by the test fixture.",
  "settings": {
    "apiKeyHelper": "${helper}",
    "env": {
      "ANTHROPIC_BASE_URL": "https://gateway.example.invalid/anthropic",
      "ANTHROPIC_DEFAULT_OPUS_MODEL": "example-large",
      "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "Example Large"
    }
  }
}
PROFILE
}

#######################################
# Write a helper that records having run, so a test can prove nothing ran it.
# Arguments:
#   $1: the sentinel path the helper touches when executed.
# Outputs:
#   The helper's path on STDOUT.
#######################################
write_tattling_helper() {
  local sentinel="$1"
  local helper="${HARNESS_TEST_DIR}/helper/tattling-api-key.sh"
  mkdir -p "${HARNESS_TEST_DIR}/helper"
  cat >"${helper}" <<HELPER
#!/bin/bash
: > "${sentinel}"
printf 'placeholder-not-a-real-credential'
HELPER
  chmod 700 "${helper}"
  printf '%s\n' "${helper}"
}
