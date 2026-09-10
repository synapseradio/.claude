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
#   - anchored to command position, optionally behind one bare wrapper word
#     (sudo, nohup, time, and the like), so the pattern inside a quoted
#     argument does not trigger a denial
#
# The wrapper word is bare by necessity: nothing in a regex distinguishes
# `sudo` from `echo`, so `echo sed -i s/a/b/ f.txt` is denied even though it
# edits nothing. That is the accepted cost. Losing `sudo sed -i` would be a
# real edit going through unguarded; a denied `echo` is rephrased in one line.
# `tests/deny-inplace-stream-edit.bats` pins both halves of the trade.
#
# Read-only stream editing in a pipeline stays allowed.
#
# The guard carries its whole reason in the denial message below, and names
# no file outside this plugin.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.

set -euo pipefail

readonly INPLACE_PATTERN='(^|[|;&(])[[:space:]]*([A-Za-z0-9_.-]+[[:space:]]+)?(g?sed[[:space:]]+(-[a-zA-Z0-9.]*i|--in-place)|awk[[:space:]]+-i[[:space:]]+inplace)'

readonly DENIAL_REASON='An in-place stream edit rewrites the file without reporting a failed match, so a wrong pattern mangles the rest of it silently. Use Edit or Write instead: they match exactly and fail loudly on a wrong match. Read-only stream editing in a pipeline stays allowed.'

main() {
  local command
  command="$(jq -r '.tool_input.command // ""')"

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
