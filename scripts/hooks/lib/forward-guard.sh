#!/bin/bash
# shellcheck shell=bash
#
# Forward an old bash-guards hook path to the plugin's copy of that guard.
#
# The live `settings.json` is untracked, so a checkout that moved a guard's
# code reaches a running session before anyone rewrites the command naming it.
# A PreToolUse command resolving to nothing is not an error the harness
# reports: the tool call simply proceeds, so every Bash call would run with
# the secret guards silently absent. Each stub under `scripts/hooks/` keeps
# the old path executable and hands stdin and stdout to the plugin's guard of
# the same name.
#
# A target that is not there is answered with `ask`, not `deny` and not
# silence. Silence is the hazard this file exists for. `deny` would brick the
# session, since repairing the settings file itself needs a tool call. `ask`
# puts the missing guard in front of the user with a way forward.
#
# Usage: forward_guard "${BASH_SOURCE[0]}" "$@"

forward_guard() {
  local stub="$1"
  shift

  local guard repo_root target
  guard="$(basename "${stub}")"
  repo_root="$(cd "$(dirname "${stub}")/../.." && pwd)"
  target="${repo_root}/features/bash-guards/hooks/${guard}"

  if [[ -f "${target}" ]]; then
    exec bash "${target}" "$@"
  fi

  local reason
  reason="The bash-guards check ${guard} did not run: there is nothing at ${target}, \
and the settings file still names the forwarder at ${stub}. Read the command yourself \
before approving it, then install the bash-guards plugin and point the settings file's \
PreToolUse hooks at the plugin's own copies."

  jq -nc --arg reason "${reason}" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}
