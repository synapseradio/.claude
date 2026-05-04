#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Reads the hook input JSON from stdin, extracts the proposed shell command,
# and refuses (permissionDecision: "deny") when that command would print an
# environment variable whose name matches a secret-shaped pattern such as
# *API_KEY*, *TOKEN*, *SECRET*, *PASSWORD*, *CREDENTIAL*, *PRIVATE_KEY*, etc.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (deny is communicated via stdout, not exit code).

set -euo pipefail

readonly SECRET_WORD='(API_?KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE_?KEY|ACCESS_?KEY|AUTH_?TOKEN|SESSION_?TOKEN|BEARER)'

# Commands whose primary purpose is emitting their arguments to stdout/stderr.
# `jq` and `awk` are included because they are commonly used to interpolate
# variables into output. `set` and `declare`/`export` without args also dump
# the environment.
readonly OUTPUT_CMD='(echo|printf|print|cat|tee|jq|awk|yes)'

#######################################
# Emit a deny decision and exit.
# Arguments:
#   $1 - human-readable reason shown in the permission prompt UI.
#######################################
deny() {
  local reason="$1"
  jq -nc --arg r "${reason}" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

main() {
  local input cmd
  input="$(cat)"
  cmd="$(jq -r '.tool_input.command // ""' <<<"${input}")"

  if [[ -z "${cmd}" ]]; then
    exit 0
  fi

  # Pattern A: an output-style command on the same logical line as a
  # dollar-reference (with or without braces, with or without parameter
  # expansion modifiers like :+ or :-) to a secret-shaped var. ripgrep is
  # used because bash's =~ ERE engine lacks \b word boundaries.
  if rg -q \
    "\b${OUTPUT_CMD}\b[^|;&]*\\\$\{?[A-Za-z_]*${SECRET_WORD}[A-Za-z_0-9]*" \
    <<<"${cmd}"; then
    deny "Refused: command would print an env var matching a secret pattern (API_KEY/TOKEN/SECRET/...). If this is intentional, run it yourself."
  fi

  # Pattern B: printenv (its sole purpose is showing env), or `env` used as
  # an output command (alone, piped, or redirected) rather than to launch a
  # subprocess. `env CMD ARGS` remains allowed.
  if rg -q '\bprintenv\b' <<<"${cmd}"; then
    deny "Refused: printenv would print env vars to stdout. If this is intentional, run it yourself."
  fi
  if rg -q '(^|[;&|`(])[[:space:]]*env[[:space:]]*(\||;|&|>|$)' <<<"${cmd}"; then
    deny "Refused: bare 'env' would dump every env var to stdout. If this is intentional, run it yourself."
  fi

  # Pattern C: `set` with no args dumps every shell variable.
  if rg -q '(^|[;&|`(])[[:space:]]*set[[:space:]]*(\||;|&|>|$)' <<<"${cmd}"; then
    deny "Refused: bare 'set' would dump every shell variable. If this is intentional, run it yourself."
  fi

  exit 0
}

main "$@"
