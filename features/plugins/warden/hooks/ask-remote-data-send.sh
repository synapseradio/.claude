#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Reads the hook input JSON from stdin, extracts the proposed shell command,
# and prompts (permissionDecision: "ask") when curl would send a request body
# or a file to a host outside loopback. A read-only fetch stays silent, so
# reading documentation over the network goes unprompted.
#
# Coverage is conservative, and doubt resolves toward asking:
#   - curl anchored to command position, optionally behind one bare wrapper
#     word (nohup, time, sudo, and the like), so the name inside a quoted
#     argument does not trigger a prompt
#   - a body flag (-d, --data*, --json), an upload flag (-T, --upload-file),
#     a form flag (-F, --form*), or a mutating method (-X POST and kin)
#   - every http and https target must parse as loopback to stay silent, so a
#     command carrying no recognizable target prompts
#
# Permission rules cannot express this, because ask beats allow with no
# exception for a more specific rule.
# https://code.claude.com/docs/en/permissions
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when asking; nothing when staying silent.
# Exit:    0 in all cases (the decision travels on stdout, not the exit code).

set -euo pipefail

readonly CURL_AT_COMMAND_POSITION='(^|[|;&(`]|\$\()[[:space:]]*([A-Za-z0-9_.-]+[[:space:]]+)?curl[[:space:]]'

readonly DATA_SEND_FLAG='(^|[[:space:]])(-[a-zA-Z]*[dFT][a-zA-Z]*([[:space:]]|=|$)|--(data[a-z-]*|json|form[a-z-]*|upload-file)([[:space:]]|=|$)|(-X|--request)[[:space:]]*(POST|PUT|PATCH|DELETE))'

readonly URL_TOKEN='https?://[^[:space:]"'\''`]+'

readonly ASK_REASON='This curl would send a request body or a file to a host outside loopback, which can carry local data off the machine. Confirm the target and the payload before it runs.'

#######################################
# Report whether a URL addresses the loopback interface.
# Arguments:
#   $1 - a URL carrying an http or https scheme.
# Returns:
#   0 when the host is loopback, 1 otherwise.
#######################################
is_loopback() {
  local url="$1"
  local host="${url#*://}"
  host="${host%%/*}"
  host="${host##*@}"

  [[ "${host}" =~ ^(localhost|127(\.[0-9]{1,3}){3}|0\.0\.0\.0|\[::1\]|[a-zA-Z0-9-]+\.localhost)(:[0-9]+)?$ ]]
}

#######################################
# Emit an ask decision and exit.
# Outputs:
#   The permission decision JSON on stdout.
#######################################
ask() {
  jq -nc --arg r "${ASK_REASON}" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"ask",permissionDecisionReason:$r}}'
  exit 0
}

main() {
  local command
  command="$(jq -r '.tool_input.command // ""')"

  if [[ -z "${command}" ]]; then
    exit 0
  fi

  if ! grep -Eq "${CURL_AT_COMMAND_POSITION}" <<<" ${command}"; then
    exit 0
  fi

  if ! grep -Eq "${DATA_SEND_FLAG}" <<<"${command}"; then
    exit 0
  fi

  # A read loop rather than mapfile, which /bin/bash 3.2 on macOS lacks.
  local -a urls=()
  local token
  while IFS= read -r token; do
    urls+=("${token}")
  done < <(grep -oE "${URL_TOKEN}" <<<"${command}" || true)

  if ((${#urls[@]} == 0)); then
    ask
  fi

  local url
  for url in "${urls[@]}"; do
    if ! is_loopback "${url}"; then
      ask
    fi
  done

  exit 0
}

main "$@"
