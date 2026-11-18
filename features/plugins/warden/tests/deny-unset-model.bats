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
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard deny-unset-model
  isolate_home

  export CLAUDE_CONFIG_DIR="${BATS_TEST_TMPDIR}/config"
  mkdir -p "${CLAUDE_CONFIG_DIR}/agents" "${CLAUDE_CONFIG_DIR}/plugins" \
    "${BATS_TEST_TMPDIR}/project/.claude/agents" \
    "${BATS_TEST_TMPDIR}/install/agents"
  json_quote "${BATS_TEST_TMPDIR}/install"
  printf '{"version":2,"plugins":{"lenses@market":[{"scope":"user","installPath":%s}]}}\n' \
    "${JSON_TEXT}" >"${CLAUDE_CONFIG_DIR}/plugins/installed_plugins.json"
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

@test "a spawn that sets a model, a fork, and haiku on other agent types stay silent" {
  local -a forms=(
    '{"prompt":"p","subagent_type":"general-purpose","model":"sonnet"}'
    '{"prompt":"p","subagent_type":"fork"}'
    '{"prompt":"p","subagent_type":"critic","model":"sonnet"}'
    '{"prompt":"p","subagent_type":"critic","model":"opus"}'
    '{"prompt":"p","subagent_type":"Plan","model":"opus"}'
    '{"prompt":"p","subagent_type":"scout","model":"haiku"}'
    '{"prompt":"p","subagent_type":"planner","model":"haiku"}'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent_agent "${form}"
  done
}

@test "a spawn that names no model is denied" {
  local -a forms=(
    '{"prompt":"p","subagent_type":"general-purpose"}'
    '{"prompt":"p"}'
    '{"prompt":"p","subagent_type":"Explore","model":""}'
    '{"prompt":"p","subagent_type":"Plan"}'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies_agent "${form}"
  done
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

@test "a critic or Plan spawned on haiku is denied" {
  local -a forms=(
    '{"prompt":"p","subagent_type":"critic","model":"haiku"}'
    '{"prompt":"p","subagent_type":"Plan","model":"haiku"}'
    '{"prompt":"p","subagent_type":"critic","model":"claude-haiku-4-5"}'
    '{"prompt":"p","subagent_type":"critic","model":"Haiku"}'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies_agent "${form}"
  done
}

@test "a critic whose definition pins haiku and sets no model is denied" {
  write_agent "${CLAUDE_CONFIG_DIR}/agents" critic critic haiku
  assert_denies_agent '{"prompt":"p","subagent_type":"critic"}'
}

@test "a critic whose definition pins haiku is allowed when the call sets sonnet" {
  write_agent "${CLAUDE_CONFIG_DIR}/agents" critic critic haiku
  assert_silent_agent '{"prompt":"p","subagent_type":"critic","model":"sonnet"}'
}

@test "a critic whose definition pins sonnet and sets no model stays silent" {
  write_agent "${CLAUDE_CONFIG_DIR}/agents" critic critic sonnet
  assert_silent_agent '{"prompt":"p","subagent_type":"critic"}'
}

@test "an envelope proposing a critic that its project pins to haiku prints a PreToolUse denial" {
  write_agent "${BATS_TEST_TMPDIR}/project/.claude/agents" critic critic haiku
  assert_main_prints deny \
    "{\"tool_name\":\"Agent\",\"cwd\":\"${BATS_TEST_TMPDIR}/project\",\"tool_input\":{\"prompt\":\"p\",\"subagent_type\":\"critic\"}}"
}
