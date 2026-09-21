#!/bin/bash
#
# PreToolUse hook: deny an Agent spawn that names no model.
#
# A spawn with no model runs on the definition's model, else on the main
# conversation's, so a session on Opus spawns every delegate on Opus. A fork
# passes, since it shares the caller's model by design, and so does a spawn
# of an agent whose definition pins a model other than inherit.
# Model resolution order: https://code.claude.com/docs/en/sub-agents.md#choose-a-model

set -euo pipefail

readonly DENIAL_REASON='This spawn names no model, and no agent definition it names pins one. Set model on the Agent call by the agent-delegation rule: haiku for reads, maps, lists, summaries, and stated changes verified by reading the output; sonnet for implementing from a design, refining a diff, and critiquing; opus for designs, plans, and irreversible edits. A fork, subagent_type fork, leaves model unset, and so does a spawn of an agent whose definition pins a model.'

#######################################
# Print what an agent file pins: its model, "none", or nothing at all when
# the frontmatter carries another name.
# Arguments:
#   $1 - the agent file.
#   $2 - the agent name the frontmatter must carry.
#######################################
pinned_model_in() {
  local file="$1" name="$2"
  awk -v want="${name}" '
    /^---[[:space:]]*$/ { fences++; if (fences == 2) exit; next }
    fences != 1 { next }
    /^name:/  { sub(/^name:[[:space:]]*/, ""); gsub(/["\047[:space:]]/, ""); seen = $0 }
    /^model:/ { sub(/^model:[[:space:]]*/, ""); gsub(/["\047[:space:]]/, ""); model = $0 }
    END {
      if (seen != want) exit
      print (model == "" || model == "inherit") ? "none" : model
    }
  ' "${file}"
}

#######################################
# Print each agents directory that could define a subagent type.
# Globals:
#   CLAUDE_CONFIG_DIR, HOME
# Arguments:
#   $1 - the subagent type.
#   $2 - the session's working directory.
#######################################
agent_dirs_for() {
  local type="$1" cwd="$2" config plugin
  config="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"

  if [[ "${type}" == *:* ]]; then
    plugin="${type%%:*}"
    [[ -f "${config}/plugins/installed_plugins.json" ]] || return 0
    jq -r --arg p "${plugin}" '
      .plugins // {} | to_entries[]
      | select(.key | split("@")[0] == $p)
      | .value[].installPath // empty
      | . + "/agents"
    ' "${config}/plugins/installed_plugins.json"
    return 0
  fi

  printf '%s\n' "${config}/agents"
  if [[ -n "${cwd}" ]]; then
    printf '%s\n' "${cwd}/.claude/agents"
  fi
}

#######################################
# Succeed when every definition found for a subagent type pins a model.
# Arguments:
#   $1 - the subagent type.
#   $2 - the session's working directory.
#######################################
definition_pins_model() {
  local type="$1" cwd="$2" name dir file pin found=0
  name="${type#*:}"
  while IFS= read -r dir; do
    [[ -d "${dir}" ]] || continue
    for file in "${dir}"/*.md; do
      [[ -f "${file}" ]] || continue
      pin="$(pinned_model_in "${file}" "${name}")"
      [[ -n "${pin}" ]] || continue
      [[ "${pin}" != 'none' ]] || return 1
      found=1
    done
  done < <(agent_dirs_for "${type}" "${cwd}")
  ((found == 1))
}

main() {
  local input model type cwd
  input="$(cat)"
  model="$(jq -r '.tool_input.model // ""' <<<"${input}")"
  type="$(jq -r '.tool_input.subagent_type // ""' <<<"${input}")"
  cwd="$(jq -r '.cwd // ""' <<<"${input}")"

  if [[ -n "${model}" || "${type}" == 'fork' ]]; then
    return 0
  fi

  if [[ -n "${type}" ]] && definition_pins_model "${type}" "${cwd}"; then
    return 0
  fi

  jq -nc --arg reason "${DENIAL_REASON}" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  return 0
}

main "$@"
