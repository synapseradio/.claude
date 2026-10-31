#!/usr/bin/env bats
#
# The guards, tested by removing what they guard.
#
# A guard that passes proves nothing on its own. Each test here builds a
# throwaway git repository, plants the breach the guard exists to catch, and
# requires the guard to fail. Then it repairs the breach and requires the
# guard to pass.

bats_require_minimum_version 1.5.0

setup() {
  load 'helpers/fixture'
  fixture_setup
  REPO="${HARNESS_TEST_DIR}/repo"
  mkdir -p "${REPO}"
  git -C "${REPO}" init -q
  git -C "${REPO}" config user.email "fixture@example.invalid"
  git -C "${REPO}" config user.name "Fixture"
}

teardown() {
  fixture_teardown
}

#######################################
# Copy the plugin into the throwaway repository, so the guard resolves its
# own root inside a repository the test owns rather than the real one.
# Outputs:
#   The copied plugin's scripts directory on STDOUT.
#######################################
plant_plugin() {
  mkdir -p "${REPO}/features"
  cp -R "${HARNESS_PLUGIN_DIR}" "${REPO}/features/harness-config"
  printf '%s\n' "${REPO}/features/harness-config/scripts"
}

write_good_ignore() {
  cat >"${REPO}/.gitignore" <<'RULES'
*
!.gitignore
!features/
!features/**
settings.json
settings.*.json
!settings.base.json
**/profiles/*.json
*api-key*.sh
*api_key*.sh
!*api-key*.template.sh
RULES
}

# bats test_tags=security
@test "the ignore guard passes when the variant rules are present" {
  local scripts
  scripts="$(plant_plugin)"
  write_good_ignore
  run env CLAUDE_PLUGIN_ROOT="${REPO}/features/harness-config" \
    bash "${scripts}/harness-guard.sh" ignore
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"pass  every-variant-name-ignored"* ]]
}

# bats test_tags=security
@test "the ignore guard fails when the variant rules are removed" {
  local scripts
  scripts="$(plant_plugin)"
  # An allowlist with no variant rule: exactly the state this plugin's
  # .gitignore was in before the rules landed, once features/** was admitted.
  cat >"${REPO}/.gitignore" <<'RULES'
*
!.gitignore
!features/
!features/**
RULES
  run env CLAUDE_PLUGIN_ROOT="${REPO}/features/harness-config" \
    bash "${scripts}/harness-guard.sh" ignore
  [ "${status}" -eq 8 ]
  [[ "${output}" == *"fail  every-variant-name-ignored"* ]]
}

# bats test_tags=security
@test "the ignore guard fails when an allowlist entry re-admits a variant" {
  local scripts
  scripts="$(plant_plugin)"
  # The rules are present, and one later line undoes them. A later rule wins,
  # so this is the ordering mistake the guard has to catch.
  write_good_ignore
  printf '!settings.gemma.json\n' >>"${REPO}/.gitignore"
  run env CLAUDE_PLUGIN_ROOT="${REPO}/features/harness-config" \
    bash "${scripts}/harness-guard.sh" ignore
  [ "${status}" -eq 8 ]
  [[ "${output}" == *"fail  every-variant-name-ignored"* ]]
}

# bats test_tags=security
@test "the ignore guard fails when a variant is already tracked" {
  local scripts
  scripts="$(plant_plugin)"
  write_good_ignore
  printf '{}\n' >"${REPO}/settings.zai.json"
  git -C "${REPO}" add -f settings.zai.json
  run env CLAUDE_PLUGIN_ROOT="${REPO}/features/harness-config" \
    bash "${scripts}/harness-guard.sh" ignore
  [ "${status}" -eq 8 ]
  [[ "${output}" == *"fail  no-variant-tracked"* ]]
}

# bats test_tags=security
@test "the material guard fails on a credential shape in a scanned file" {
  local dir="${HARNESS_TEST_DIR}/scan"
  mkdir -p "${dir}"
  # A credential-prefixed string assembled here rather than written whole, so
  # this test file itself carries no credential shape for its own guard to
  # find.
  printf 'token = %s%s\n' 'sk-' 'abcdefghijklmnopqrstuvwx' >"${dir}/leaked.json"
  run bash "$(harness_scripts)/harness-guard.sh" material "${dir}"
  [ "${status}" -eq 9 ]
  [[ "${output}" == *"fail  credential-prefix"* ]]
}

# bats test_tags=security
@test "the material guard fails on an absolute home path in a scanned file" {
  local dir="${HARNESS_TEST_DIR}/scan"
  mkdir -p "${dir}"
  printf 'helper = %s/somebody/.config/api-key.sh\n' '/Users' >"${dir}/pathy.md"
  run bash "$(harness_scripts)/harness-guard.sh" material "${dir}"
  [ "${status}" -eq 9 ]
  [[ "${output}" == *"fail  home-absolute-path"* ]]
}

# bats test_tags=security
@test "the material guard names the file and never the matched text" {
  local dir="${HARNESS_TEST_DIR}/scan"
  mkdir -p "${dir}"
  printf 'token = %s%s\n' 'sk-' 'abcdefghijklmnopqrstuvwx' >"${dir}/leaked.json"
  run bash "$(harness_scripts)/harness-guard.sh" material "${dir}"
  [ "${status}" -eq 9 ]
  [[ "${output}" == *"leaked.json"* ]]
  # Reporting the match would make running the scan a way to publish what it
  # found, so the scan reports paths alone.
  [[ "${output}" != *"abcdefghijklmnopqrstuvwx"* ]]
}

# bats test_tags=security
@test "the material guard passes on a directory holding nothing account-bound" {
  local dir="${HARNESS_TEST_DIR}/scan"
  mkdir -p "${dir}"
  printf 'endpoint = https://gateway.example.invalid\n' >"${dir}/fine.md"
  run bash "$(harness_scripts)/harness-guard.sh" material "${dir}"
  [ "${status}" -eq 0 ]
}

# bats test_tags=security
@test "the script guard fails on a script that cats a settings file" {
  local scripts
  scripts="$(plant_plugin)"
  printf '#!/bin/bash\ncat "${HOME}/.claude/settings.json"\n' \
    >"${REPO}/features/harness-config/scripts/rogue.sh"
  run env CLAUDE_PLUGIN_ROOT="${REPO}/features/harness-config" \
    bash "${scripts}/harness-guard.sh" scripts
  [ "${status}" -eq 10 ]
  [[ "${output}" == *"fail  no-cat-of-a-settings-file"* ]]
}

# bats test_tags=security
@test "the script guard fails on a script that runs an api key helper" {
  local scripts
  scripts="$(plant_plugin)"
  printf '#!/bin/bash\ntoken="$(${helper})"\n' \
    >"${REPO}/features/harness-config/scripts/rogue.sh"
  run env CLAUDE_PLUGIN_ROOT="${REPO}/features/harness-config" \
    bash "${scripts}/harness-guard.sh" scripts
  [ "${status}" -eq 10 ]
  [[ "${output}" == *"fail  no-helper-execution"* ]]
}

# bats test_tags=security
@test "the script guard fails when the helper template ships executable" {
  local scripts
  scripts="$(plant_plugin)"
  chmod 755 "${REPO}/features/harness-config/templates/api-key-helper.template.sh"
  run env CLAUDE_PLUGIN_ROOT="${REPO}/features/harness-config" \
    bash "${scripts}/harness-guard.sh" scripts
  [ "${status}" -eq 10 ]
  [[ "${output}" == *"fail  template-not-executable"* ]]
}

# bats test_tags=security
@test "the script guard passes on the plugin as it ships" {
  local scripts
  scripts="$(plant_plugin)"
  run env CLAUDE_PLUGIN_ROOT="${REPO}/features/harness-config" \
    bash "${scripts}/harness-guard.sh" scripts
  [ "${status}" -eq 0 ]
}
