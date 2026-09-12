#!/usr/bin/env bats
#
# Setup counts the deny rules it would add before it adds any.
#
# The expected counts come from docs/design.md: setup merges five deny rules
# into settings.base.json and removes none, so the number it reports is five
# minus however many the floor already holds.

bats_require_minimum_version 1.5.0

setup() {
  load 'helpers/fixture'
  fixture_setup
  REPO="${HARNESS_TEST_DIR}/repo"
  mkdir -p "${REPO}/features"
  git -C "${REPO}" init -q
  cp -R "${HARNESS_PLUGIN_DIR}" "${REPO}/features/harness-config"
  export CLAUDE_PLUGIN_ROOT="${REPO}/features/harness-config"
  SCRIPTS="${CLAUDE_PLUGIN_ROOT}/scripts"
}

teardown() {
  fixture_teardown
}

# bats test_tags=unit
@test "setup dry run reports five deny rules to add when the floor holds none" {
  run bash "${SCRIPTS}/harness-setup.sh" --dry-run
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"would-add"*"5 deny rule(s)"* ]]
}

# bats test_tags=unit
@test "setup dry run reports only the deny rules the floor lacks" {
  jq '.permissions.deny = ["Read(**/settings.json)", "Read(~/.claude/plugins/data/**)"]' \
    "${CLAUDE_CONFIG_DIR}/settings.base.json" >"${CLAUDE_CONFIG_DIR}/base.tmp"
  mv "${CLAUDE_CONFIG_DIR}/base.tmp" "${CLAUDE_CONFIG_DIR}/settings.base.json"
  run bash "${SCRIPTS}/harness-setup.sh" --dry-run
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"would-add"*"3 deny rule(s)"* ]]
}

# bats test_tags=unit
@test "setup dry run reports every deny rule present when the floor holds all five" {
  jq '.permissions.deny = [
    "Read(**/settings.json)",
    "Read(**/settings.*.json)",
    "Read(~/.claude/agents/**)",
    "Read(**/.claude/agents/**)",
    "Read(~/.claude/plugins/data/**)"
  ]' "${CLAUDE_CONFIG_DIR}/settings.base.json" >"${CLAUDE_CONFIG_DIR}/base.tmp"
  mv "${CLAUDE_CONFIG_DIR}/base.tmp" "${CLAUDE_CONFIG_DIR}/settings.base.json"
  run bash "${SCRIPTS}/harness-setup.sh" --dry-run
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"deny-rules"*"already present"* ]]
}

# bats test_tags=integration
@test "setup appends the deny rules after the floor's own and reorders none" {
  jq '.permissions.deny = ["Bash(sudo *)", "Bash(rm -rf /*)", "Read(~/.claude/plugins/data/**)"]' \
    "${CLAUDE_CONFIG_DIR}/settings.base.json" >"${CLAUDE_CONFIG_DIR}/base.tmp"
  mv "${CLAUDE_CONFIG_DIR}/base.tmp" "${CLAUDE_CONFIG_DIR}/settings.base.json"
  run bash "${SCRIPTS}/harness-setup.sh"
  [ "${status}" -eq 0 ]
  run jq -c '.permissions.deny' "${CLAUDE_CONFIG_DIR}/settings.base.json"
  # The floor's own order survives, "sudo" ahead of "rm" ahead of the rule it
  # already held, and the four it lacked follow in the fragment's order.
  [ "${output}" = '["Bash(sudo *)","Bash(rm -rf /*)","Read(~/.claude/plugins/data/**)","Read(**/settings.json)","Read(**/settings.*.json)","Read(~/.claude/agents/**)","Read(**/.claude/agents/**)"]' ]
}
