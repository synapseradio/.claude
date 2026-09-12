#!/usr/bin/env bats
#
# The apply script runs the Reconcile machine over a variant with no human
# in the loop, and halts before writing whenever the machine would have
# asked one a question.
#
# Expected values come from the classification table and the Seal rules in
# skills/update-claude-settings/references/alignment-machine.md, never from
# the script under test.

bats_require_minimum_version 1.5.0

setup() {
  load 'helpers/fixture'
  fixture_setup
  APPLY="$(harness_scripts)/harness-align-apply.sh"
  BASE="${CLAUDE_CONFIG_DIR}/settings.base.json"
}

teardown() {
  fixture_teardown
}

# Rewrite the synthetic floor through a jq program.
set_base() {
  jq "$1" "${BASE}" >"${CLAUDE_CONFIG_DIR}/base.tmp"
  mv "${CLAUDE_CONFIG_DIR}/base.tmp" "${BASE}"
}

# Write a variant by basename from stdin.
write_variant() {
  cat >"${CLAUDE_CONFIG_DIR}/$1"
}

# Evaluate a jq program against a variant, compact output.
variant_jq() {
  jq -c "$2" "${CLAUDE_CONFIG_DIR}/$1"
}

# bats test_tags=unit
@test "apply adds a leaf the floor names when the variant lacks it" {
  write_variant settings.glm.json <<'JSON'
{ "model": "example-model" }
JSON
  run bash "${APPLY}"
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"add"*"env.CLAUDE_CODE_ENABLE_TELEMETRY"* ]]
  [ "$(variant_jq settings.glm.json '.env.CLAUDE_CODE_ENABLE_TELEMETRY')" = '"1"' ]
  [ "$(variant_jq settings.glm.json '.model')" = '"example-model"' ]
}

# bats test_tags=unit
@test "apply corrects a member to the floor's spelling when the two normalize alike" {
  set_base '.sandbox = { "filesystem": { "allowWrite": ["/tmp", "~/.notes"] } }'
  write_variant settings.glm.json <<'JSON'
{
  "env": { "CLAUDE_CODE_ENABLE_TELEMETRY": "1" },
  "permissions": { "allow": ["Bash(jq:*)"], "ask": [], "deny": [] },
  "sandbox": { "filesystem": { "allowWrite": ["//.notes", "//tmp", "/var/tmp"] } }
}
JSON
  run bash "${APPLY}"
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"corrected"*"sandbox.filesystem.allowWrite"* ]]
  # The floor's members lead in the floor's order and spelling; the member
  # only the variant names follows.
  [ "$(variant_jq settings.glm.json '.sandbox.filesystem.allowWrite')" = '["/tmp","~/.notes","/var/tmp"]' ]
}

# bats test_tags=unit
@test "apply collapses two hook groups sharing a matcher and adds the floor's hook" {
  set_base '.hooks = { "PostToolUse": [ { "hooks": [ { "type": "command", "command": "python3 x.py" } ] } ] }'
  write_variant settings.glm.json <<'JSON'
{
  "env": { "CLAUDE_CODE_ENABLE_TELEMETRY": "1" },
  "permissions": { "allow": ["Bash(jq:*)"], "ask": [], "deny": [] },
  "hooks": {
    "PostToolUse": [
      { "hooks": [ { "type": "command", "command": "a.sh" } ] },
      { "hooks": [ { "type": "command", "command": "b.sh" } ] }
    ]
  }
}
JSON
  run bash "${APPLY}"
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"collapsed"*"hooks.PostToolUse"* ]]
  [ "$(variant_jq settings.glm.json '.hooks.PostToolUse | length')" = '1' ]
  [ "$(variant_jq settings.glm.json '.hooks.PostToolUse[0].hooks | map(.command)')" = '["python3 x.py","a.sh","b.sh"]' ]
}

# bats test_tags=unit
@test "apply corrects a hook command to the floor's spelling when the two normalize alike" {
  set_base '.hooks = { "PostToolUse": [ { "hooks": [ { "type": "command", "command": "python3.14 $HOME/.claude/scripts/hooks/x.py", "timeout": 5 } ] } ] }'
  write_variant settings.glm.json <<'JSON'
{
  "env": { "CLAUDE_CODE_ENABLE_TELEMETRY": "1" },
  "permissions": { "allow": ["Bash(jq:*)"], "ask": [], "deny": [] },
  "hooks": {
    "PostToolUse": [
      { "hooks": [ { "type": "command", "command": "python3 $HOME/.claude/scripts/hooks/x.py", "timeout": 5 } ] }
    ]
  }
}
JSON
  run bash "${APPLY}"
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"corrected"*"hooks.PostToolUse.hooks.command"* ]]
  [ "$(variant_jq settings.glm.json '.hooks.PostToolUse[0].hooks | map(.command)')" = '["python3.14 $HOME/.claude/scripts/hooks/x.py"]' ]
}

# bats test_tags=unit
@test "apply removes an entry from allow when the floor denies it" {
  set_base '.permissions.deny = ["WebFetch"]'
  write_variant settings.glm.json <<'JSON'
{
  "env": { "CLAUDE_CODE_ENABLE_TELEMETRY": "1" },
  "permissions": { "allow": ["Bash(jq:*)", "WebFetch", "Read"], "ask": [], "deny": [] }
}
JSON
  run bash "${APPLY}"
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"removed"*"permissions.allow"* ]]
  [[ "${output}" != *"WebFetch"* ]]
  [ "$(variant_jq settings.glm.json '.permissions.allow')" = '["Bash(jq:*)","Read"]' ]
  [ "$(variant_jq settings.glm.json '.permissions.deny')" = '["WebFetch"]' ]
}

# bats test_tags=unit
@test "apply halts without writing when a scalar conflicts" {
  write_variant settings.glm.json <<'JSON'
{ "env": { "CLAUDE_CODE_ENABLE_TELEMETRY": "conflicting-sentinel-value" } }
JSON
  cp "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/before.json"
  run bash "${APPLY}"
  [ "${status}" -eq 13 ]
  [[ "${output}" == *"conflict"*"scalar"*"env.CLAUDE_CODE_ENABLE_TELEMETRY"* ]]
  [[ "${output}" != *"conflicting-sentinel-value"* ]]
  cmp -s "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/before.json"
}

# bats test_tags=unit
@test "apply halts with a coupled conflict when an entry sits in two lists the floor names in none" {
  write_variant settings.glm.json <<'JSON'
{
  "env": { "CLAUDE_CODE_ENABLE_TELEMETRY": "1" },
  "permissions": { "allow": ["Bash(jq:*)", "WebSearch"], "ask": ["WebSearch"], "deny": [] }
}
JSON
  cp "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/before.json"
  run bash "${APPLY}"
  [ "${status}" -eq 13 ]
  [[ "${output}" == *"conflict"*"coupled"*"permissions"* ]]
  [[ "${output}" != *"WebSearch"* ]]
  cmp -s "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/before.json"
}

# bats test_tags=integration
@test "apply writes a backup under the data directory before overwriting" {
  write_variant settings.glm.json <<'JSON'
{ "model": "example-model" }
JSON
  cp "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/before.json"
  run bash "${APPLY}"
  [ "${status}" -eq 0 ]
  local -a backups=("${HARNESS_CONFIG_DATA}"/backups/settings.glm.json.pre-*.json)
  [ "${#backups[@]}" -eq 1 ]
  cmp -s "${backups[0]}" "${HARNESS_TEST_DIR}/before.json"
}

# bats test_tags=integration
@test "apply leaves a second run with nothing to write" {
  write_variant settings.glm.json <<'JSON'
{ "model": "example-model" }
JSON
  run bash "${APPLY}"
  [ "${status}" -eq 0 ]
  cp "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/after-first.json"
  run bash "${APPLY}"
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"aligned"* ]]
  [[ "${output}" != *"written"* ]]
  cmp -s "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/after-first.json"
  local -a backups=("${HARNESS_CONFIG_DATA}"/backups/settings.glm.json.pre-*.json)
  [ "${#backups[@]}" -eq 1 ]
}

# bats test_tags=unit
@test "apply dry run reports the write and performs none" {
  write_variant settings.glm.json <<'JSON'
{ "model": "example-model" }
JSON
  cp "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/before.json"
  run bash "${APPLY}" --dry-run
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"would-write"* ]]
  cmp -s "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/before.json"
  [ ! -e "${HARNESS_CONFIG_DATA}/backups" ] || [ -z "$(ls -A "${HARNESS_CONFIG_DATA}/backups")" ]
}

# bats test_tags=unit
@test "apply output carries no settings value" {
  write_variant settings.glm.json <<'JSON'
{
  "model": "sentinel-model-9f2a",
  "env": { "ANTHROPIC_AUTH_TOKEN": "placeholder-not-a-real-credential-77" }
}
JSON
  run bash "${APPLY}"
  [ "${status}" -eq 0 ]
  [[ "${output}" != *"sentinel-model-9f2a"* ]]
  [[ "${output}" != *"placeholder-not-a-real-credential-77"* ]]
  [ "$(variant_jq settings.glm.json '.model')" = '"sentinel-model-9f2a"' ]
  [ "$(variant_jq settings.glm.json '.env.ANTHROPIC_AUTH_TOKEN')" = '"placeholder-not-a-real-credential-77"' ]
}

# bats test_tags=unit
@test "apply skips a file the registry lists under notAVariant" {
  write_variant settings.local.json <<'JSON'
{ "model": "example-model" }
JSON
  write_variant settings.glm.json <<'JSON'
{ "model": "example-model" }
JSON
  cp "${CLAUDE_CONFIG_DIR}/settings.local.json" "${HARNESS_TEST_DIR}/before.json"
  run bash "${APPLY}"
  [ "${status}" -eq 0 ]
  [[ "${output}" != *"settings.local.json"* ]]
  cmp -s "${CLAUDE_CONFIG_DIR}/settings.local.json" "${HARNESS_TEST_DIR}/before.json"
}

# bats test_tags=unit
@test "apply sweeps only the named variant when --variant is given" {
  write_variant settings.json <<'JSON'
{ "model": "example-model" }
JSON
  write_variant settings.glm.json <<'JSON'
{ "model": "example-model" }
JSON
  cp "${CLAUDE_CONFIG_DIR}/settings.json" "${HARNESS_TEST_DIR}/before.json"
  run bash "${APPLY}" --variant settings.glm.json
  [ "${status}" -eq 0 ]
  [[ "${output}" != *"== settings.json"* ]]
  cmp -s "${CLAUDE_CONFIG_DIR}/settings.json" "${HARNESS_TEST_DIR}/before.json"
  [ "$(variant_jq settings.glm.json '.env.CLAUDE_CODE_ENABLE_TELEMETRY')" = '"1"' ]
}

# bats test_tags=unit
@test "apply touches no variant when the floor fails its audit" {
  set_base '.permissions.deny = ["Bash(jq:*)"]'
  write_variant settings.glm.json <<'JSON'
{ "model": "example-model" }
JSON
  cp "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/before.json"
  run bash "${APPLY}"
  [ "${status}" -eq 11 ]
  [[ "${output}" == *"audit-base"* ]]
  cmp -s "${CLAUDE_CONFIG_DIR}/settings.glm.json" "${HARNESS_TEST_DIR}/before.json"
}
