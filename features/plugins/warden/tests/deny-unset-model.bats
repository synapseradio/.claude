#!/usr/bin/env bats
#
# Tests for deny-unset-model.sh, the PreToolUse Agent guard that denies a
# spawn naming no model.
#
# A spawn passes when it sets model, when it is a fork, or when the agent
# definition it names pins a model other than inherit. Definitions come from
# a temporary Claude directory, a temporary project, and a temporary plugin
# install, so no case reads the machine's own agents.

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-unset-model.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"

  export CLAUDE_CONFIG_DIR="${BATS_TEST_TMPDIR}/config"
  mkdir -p "${CLAUDE_CONFIG_DIR}/agents" "${CLAUDE_CONFIG_DIR}/plugins" \
    "${BATS_TEST_TMPDIR}/project/.claude/agents" \
    "${BATS_TEST_TMPDIR}/install/agents"
  jq -nc --arg p "${BATS_TEST_TMPDIR}/install" \
    '{version:2,plugins:{"lenses@market":[{scope:"user",installPath:$p}]}}' \
    >"${CLAUDE_CONFIG_DIR}/plugins/installed_plugins.json"
}

#######################################
# Write an agent definition.
# Arguments:
#   $1 - the directory holding agent files.
#   $2 - the file's base name.
#   $3 - the frontmatter name.
#   $4 - the frontmatter model, or empty for none.
#######################################
write_agent() {
  local dir="$1" file="$2" name="$3" model="$4"
  {
    printf -- '---\nname: %s\ndescription: a test agent\n' "${name}"
    [[ -n "${model}" ]] && printf 'model: %s\n' "${model}"
    printf -- '---\n\nBody text naming model: opus.\n'
  } >"${dir}/${file}.md"
}

@test "a spawn that sets model stays silent" {
  assert_silent_agent '{"prompt":"p","subagent_type":"general-purpose","model":"sonnet"}'
}

@test "a spawn with no model is denied" {
  assert_denies_agent '{"prompt":"p","subagent_type":"general-purpose"}'
}

@test "a spawn with no type and no model is denied" {
  assert_denies_agent '{"prompt":"p"}'
}

@test "a spawn with an empty model is denied" {
  assert_denies_agent '{"prompt":"p","subagent_type":"Explore","model":""}'
}

@test "a fork with no model stays silent" {
  assert_silent_agent '{"prompt":"p","subagent_type":"fork"}'
}

@test "a user agent pinned to haiku stays silent" {
  write_agent "${CLAUDE_CONFIG_DIR}/agents" scout scout haiku
  assert_silent_agent '{"prompt":"p","subagent_type":"scout"}'
}

@test "a user agent is found by its frontmatter name" {
  write_agent "${CLAUDE_CONFIG_DIR}/agents" web-mapper spider sonnet
  assert_silent_agent '{"prompt":"p","subagent_type":"spider"}'
}

@test "a user agent set to inherit is denied" {
  write_agent "${CLAUDE_CONFIG_DIR}/agents" critic critic inherit
  assert_denies_agent '{"prompt":"p","subagent_type":"critic"}'
}

@test "a user agent with no model line is denied" {
  write_agent "${CLAUDE_CONFIG_DIR}/agents" critic critic ''
  assert_denies_agent '{"prompt":"p","subagent_type":"critic"}'
}

@test "a project agent pinned to opus stays silent" {
  write_agent "${BATS_TEST_TMPDIR}/project/.claude/agents" planner planner opus
  assert_silent_agent '{"prompt":"p","subagent_type":"planner"}'
}

@test "a plugin agent pinned to sonnet stays silent" {
  write_agent "${BATS_TEST_TMPDIR}/install/agents" reviewer reviewer sonnet
  assert_silent_agent '{"prompt":"p","subagent_type":"lenses:reviewer"}'
}

@test "a plugin agent with no model line is denied" {
  write_agent "${BATS_TEST_TMPDIR}/install/agents" reviewer reviewer ''
  assert_denies_agent '{"prompt":"p","subagent_type":"lenses:reviewer"}'
}

@test "a pinned agent of the same name in another plugin stays denied" {
  write_agent "${BATS_TEST_TMPDIR}/install/agents" reviewer reviewer sonnet
  assert_denies_agent '{"prompt":"p","subagent_type":"other:reviewer"}'
}

@test "a denial names the tiers and the fork exemption" {
  run_agent_hook '{"prompt":"p","subagent_type":"general-purpose"}'
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'haiku'* && "${reason}" == *'fork'* ]]
}

@test "a denial keeps file edits off haiku and git operations on it" {
  run_agent_hook '{"prompt":"p","subagent_type":"general-purpose"}'
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'verbatim copies of prepared payloads'* ]]
  [[ "${reason}" == *'git operations stated whole'* ]]
  [[ "${reason}" == *'sonnet for implementing from a design, editing files'* ]]
  [[ "${reason}" != *'stated changes verified by reading the output'* ]]
}

@test "a critic spawned on haiku is denied" {
  assert_denies_agent '{"prompt":"p","subagent_type":"critic","model":"haiku"}'
}

@test "a Plan spawned on haiku is denied" {
  assert_denies_agent '{"prompt":"p","subagent_type":"Plan","model":"haiku"}'
}

@test "a critic spawned on a full haiku model id is denied" {
  assert_denies_agent '{"prompt":"p","subagent_type":"critic","model":"claude-haiku-4-5"}'
}

@test "a critic spawned on haiku in capitals is denied" {
  assert_denies_agent '{"prompt":"p","subagent_type":"critic","model":"Haiku"}'
}

@test "a critic spawned on sonnet stays silent" {
  assert_silent_agent '{"prompt":"p","subagent_type":"critic","model":"sonnet"}'
}

@test "a critic spawned on opus stays silent" {
  assert_silent_agent '{"prompt":"p","subagent_type":"critic","model":"opus"}'
}

@test "a Plan spawned on opus stays silent" {
  assert_silent_agent '{"prompt":"p","subagent_type":"Plan","model":"opus"}'
}

@test "a haiku spawn of another agent type stays silent" {
  assert_silent_agent '{"prompt":"p","subagent_type":"scout","model":"haiku"}'
}

@test "a spawn of a similarly named planner on haiku stays silent" {
  assert_silent_agent '{"prompt":"p","subagent_type":"planner","model":"haiku"}'
}

@test "a critic whose definition pins haiku and sets no model is denied for haiku" {
  write_agent "${CLAUDE_CONFIG_DIR}/agents" critic critic haiku
  run_agent_hook '{"prompt":"p","subagent_type":"critic"}'
  assert_decision 'deny' 'critic pinned to haiku'
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'sonnet or opus'* ]]
}

@test "a critic whose definition pins haiku is allowed when the call sets sonnet" {
  write_agent "${CLAUDE_CONFIG_DIR}/agents" critic critic haiku
  assert_silent_agent '{"prompt":"p","subagent_type":"critic","model":"sonnet"}'
}

@test "a critic whose definition pins sonnet and sets no model stays silent" {
  write_agent "${CLAUDE_CONFIG_DIR}/agents" critic critic sonnet
  assert_silent_agent '{"prompt":"p","subagent_type":"critic"}'
}

@test "a Plan with no model is denied for the unset model, not for haiku" {
  run_agent_hook '{"prompt":"p","subagent_type":"Plan"}'
  assert_decision 'deny' 'Plan with no model'
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'names no model'* ]]
}

@test "a haiku denial names sonnet and opus" {
  run_agent_hook '{"prompt":"p","subagent_type":"critic","model":"haiku"}'
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'sonnet or opus'* ]]
}
