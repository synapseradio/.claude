#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Reads the hook input JSON from stdin, extracts the proposed shell command,
# and refuses (permissionDecision: "deny") when that command edits a file in
# place with a stream editor. A stream editor rewrites a file without
# reporting a failed match, so a wrong pattern mangles the rest of the file
# silently; Edit and Write fail loudly instead.
#
# Coverage is conservative:
#   - sed or gsed carrying a short-flag cluster containing i, or --in-place
#   - gawk invoked as `awk -i inplace`
#   - anchored to command position, so the pattern inside a quoted argument
#     does not trigger a denial
#
# Read-only stream editing in a pipeline stays allowed.
#
# Enforces rules/never-use-sed.md.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.

set -euo pipefail

readonly INPLACE_PATTERN='(^|[|;&(]|&&)[[:space:]]*(g?sed[[:space:]]+(-[a-zA-Z0-9.]*i|--in-place)|awk[[:space:]]+-i[[:space:]]+inplace)'

readonly DENIAL_REASON='In-place stream edits are banned by rules/never-use-sed.md. Use Edit or Write instead: they match exactly, fail loudly on a wrong match, and never silently mangle the rest of the file. Read-only stream editing in a pipeline stays allowed.'

main() {
  local input command
  input="$(cat)"
  command="$(jq -r '.tool_input.command // ""' <<<"${input}")"

  if [[ -z "${command}" ]]; then
    return 0
  fi

  if grep -Eq "${INPLACE_PATTERN}" <<<"${command}"; then
    jq -nc --arg reason "${DENIAL_REASON}" '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: $reason
      }
    }'
  fi

  return 0
}

main "$@"
