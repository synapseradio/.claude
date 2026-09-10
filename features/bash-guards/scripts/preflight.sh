#!/bin/bash
#
# Reports whether each guard in this plugin still refuses what it exists to
# refuse, still allows ordinary work, and still leaves alone the paths that
# only resemble a secret.
#
# Each case builds one PreToolUse envelope, hands it to a single guard, and
# compares the decision that comes back to the decision expected. The
# trigger text lives in this file rather than in a command anyone types,
# because the guards read the command they are given: a shell line that
# names the environment-dumping command is a line the first guard denies.
#
# A guard answers on stdout and exits 0 whatever it decides, so a guard that
# crashed and a guard that allowed both print nothing. The status is checked
# for that reason.
#
# The checks run against the machine as it stands, a banned-reads file
# included, so this reports the guards as configured rather than as shipped.
#
# Globals: HOOKS_DIR, FAILURES, DECISION, STATUS.
# Arguments: none.
# Stdout:  one line per case, then a count.
# Exit:    0 when every case matched, 1 otherwise.

set -uo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../hooks" && pwd)"
readonly HOOKS_DIR

FAILURES=0
DECISION=''
STATUS=0

#######################################
# Hand one envelope to one guard and record what it decided.
# Globals:
#   HOOKS_DIR, DECISION, STATUS
# Arguments:
#   $1 - the guard's file name.
#   $2 - the PreToolUse envelope.
#######################################
decide() {
  local guard="$1" envelope="$2" output
  STATUS=0
  output="$(bash "${HOOKS_DIR}/${guard}" <<<"${envelope}")" || STATUS=$?
  if [[ -z "${output}" ]]; then
    DECISION='allow'
    return 0
  fi
  DECISION="$(jq -r '.hookSpecificOutput.permissionDecision // "unreadable"' \
    <<<"${output}")"
}

#######################################
# Report one case against the decision it expected.
# Globals:
#   DECISION, STATUS, FAILURES
# Arguments:
#   $1 - the guard's file name.
#   $2 - the expected decision: deny, ask, or allow.
#   $3 - a label for the case.
# Outputs:
#   One result line on stdout.
#######################################
report() {
  local guard="$1" want="$2" label="$3"

  if ((STATUS != 0)); then
    printf 'FAIL  %-30s %-30s guard exited %d\n' "${guard}" "${label}" \
      "${STATUS}"
    FAILURES=$((FAILURES + 1))
    return 0
  fi

  if [[ "${DECISION}" == "${want}" ]]; then
    printf 'ok    %-30s %-30s %s\n' "${guard}" "${label}" "${DECISION}"
    return 0
  fi

  printf 'FAIL  %-30s %-30s wanted %s, got %s\n' "${guard}" "${label}" \
    "${want}" "${DECISION}"
  FAILURES=$((FAILURES + 1))
}

#######################################
# Put one proposed shell command through one guard.
# Arguments:
#   $1 - the guard's file name.
#   $2 - the expected decision.
#   $3 - a label for the case.
#   $4 - the command the Bash tool would propose.
#######################################
check() {
  local envelope
  envelope="$(jq -nc --arg c "$4" \
    '{tool_name:"Bash",tool_input:{command:$c}}')"
  decide "$1" "${envelope}"
  report "$1" "$2" "$3"
}

#######################################
# Put one proposed Read target through one guard.
# Arguments:
#   $1 - the guard's file name.
#   $2 - the expected decision.
#   $3 - a label for the case.
#   $4 - the path the Read tool would open.
#######################################
check_read() {
  local envelope
  envelope="$(jq -nc --arg p "$4" \
    '{tool_name:"Read",tool_input:{file_path:$p}}')"
  decide "$1" "${envelope}"
  report "$1" "$2" "$3"
}

main() {
  # Single quotes are intentional: the guard has to receive the literal
  # characters of a variable reference, which is what it matches on. An
  # expanded value would carry no dollar sign for it to find.
  # shellcheck disable=SC2016
  check block-secret-leaks.sh deny 'prints a secret' \
    'echo "${AWS_SECRET_ACCESS_KEY}"'
  check block-secret-leaks.sh deny 'dumps the environment' 'printenv'
  check block-secret-leaks.sh allow 'ordinary command' 'git status --short'

  check block-secret-file-reads.sh deny 'reads a private key' \
    'cat ~/.ssh/id_rsa'
  check block-secret-file-reads.sh deny 'reads an env file' 'cat .env'
  check block-secret-file-reads.sh deny 'reads a dotfiles private store' \
    'cat ~/dotfiles/shell/lib/private/keys.sh'
  check block-secret-file-reads.sh deny 'reads a secrets file' \
    'cat secrets.env'
  check block-secret-file-reads.sh allow 'reads a source file' 'cat README.md'
  check block-secret-file-reads.sh allow 'reads the real /tmp' \
    'cat /private/tmp/build.log'
  check block-secret-file-reads.sh allow 'reads a secrets-rotating script' \
    'cat scripts/rotate-secrets.sh'
  # These two expand at run time, so this file names no home directory of
  # its own. The guard reads the path as text and opens nothing, so neither
  # case touches a file whether or not one is there.
  check_read block-secret-file-reads.sh deny 'Read of a private key' \
    "${HOME}/.ssh/id_ed25519"
  check_read block-secret-file-reads.sh allow 'Read of a source file' \
    "${HOME}/projects/app/README.md"

  check deny-inplace-stream-edit.sh deny 'edits a file in place' \
    "sed -i '' 's/old/new/' notes.md"
  check deny-inplace-stream-edit.sh allow 'reads through a filter' \
    "sed -n '1,5p' notes.md"

  check ask-remote-data-send.sh ask 'sends a file off the machine' \
    'curl -X POST https://example.com/collect -d @notes.md'
  check ask-remote-data-send.sh allow 'fetches a page' \
    'curl -sfL https://example.com/docs.md'

  if ((FAILURES == 0)); then
    printf '\nEvery guard decided as expected.\n'
    return 0
  fi

  printf '\n%d case(s) came back wrong. A guard above is not doing its job.\n' \
    "${FAILURES}"
  return 1
}

main "$@"
