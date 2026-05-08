#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Reads the hook input JSON from stdin, extracts the proposed shell command,
# and refuses (permissionDecision: "deny") when that command would read a
# file at a secret-shaped path. Mirrors the permissions.deny `Read(...)`
# rules in settings.json so that the Bash tool does not bypass them when
# the OS sandbox is disabled.
#
# Coverage is conservative:
#   - SSH/AWS/GnuPG/kube directory paths (under $HOME, ~, or /Users/<user>)
#   - SSH private key filenames (id_rsa, id_ed25519, id_ecdsa, id_dsa)
#   - .env, .env.local, .env.<name>.local
#
# Out of scope (because they false-positive too aggressively in Bash):
#   - bare "credentials" / "secrets" substrings — too many legitimate paths
#     contain those words. The Read tool deny still applies for those.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (deny is communicated via stdout, not exit code).

set -euo pipefail

# Commands that read file contents from a path argument or redirect.
readonly READ_CMDS='(cat|tac|less|more|head|tail|bat|xxd|od|strings|hexdump|grep|rg|ripgrep|sed|awk|jq|yq|nl|file|wc|md5sum|sha1sum|sha256sum|sha512sum|cksum|cp|mv|install|tar|zip|gzip|bzip2|xz|7z|openssl|base64|gpg|ssh-keygen|ssh-add)'

# Path patterns. Each is matched as an extended regex against the command
# string. Patterns are deliberately anchored to avoid bare-word false
# positives.
readonly DOTDIR_USERS_PREFIX='(\$HOME|~|/Users/[^/[:space:]]+)'
readonly SSH_PATH="${DOTDIR_USERS_PREFIX}/\.ssh/"
readonly AWS_PATH="${DOTDIR_USERS_PREFIX}/\.aws/"
readonly GNUPG_PATH="${DOTDIR_USERS_PREFIX}/\.gnupg/"
readonly KUBE_PATH="${DOTDIR_USERS_PREFIX}/\.kube/"
readonly SSH_KEY_NAME='\bid_(rsa|ed25519|ecdsa|dsa)\b'
readonly ENV_FILE='(^|[[:space:]/=])\.env(\.local|\.[^.[:space:]/]+\.local)?($|[[:space:]])'

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

#######################################
# Test whether a read-style command appears on the same logical line as a
# secret path pattern. Logical lines are split on the shell separators
# `|`, `;`, `&`, and newlines.
# Arguments:
#   $1 - regex for the secret path
#   $2 - the command string
#######################################
read_cmd_hits_path() {
  local path_re="$1" cmd="$2"
  rg -q "\b${READ_CMDS}\b[^|;&"$'\n'"]*${path_re}" <<<"${cmd}"
}

#######################################
# Test whether a shell input redirect targets a secret path. Catches
# `cmd < path`, `cmd 0< path`, and similar.
# Arguments:
#   $1 - regex for the secret path
#   $2 - the command string
#######################################
redirect_hits_path() {
  local path_re="$1" cmd="$2"
  rg -q "[0-9]?<[[:space:]]*[^|;&"$'\n'"]*${path_re}" <<<"${cmd}"
}

#######################################
# Run both checks for a single path pattern. Denies on the first hit.
# Arguments:
#   $1 - human label for the deny message
#   $2 - regex for the secret path
#   $3 - the command string
#######################################
check_path() {
  local label="$1" path_re="$2" cmd="$3"
  if read_cmd_hits_path "${path_re}" "${cmd}" \
    || redirect_hits_path "${path_re}" "${cmd}"; then
    deny "Refused: command would read a secret-shaped path (${label}). If this is intentional, run it yourself."
  fi
}

main() {
  local input cmd
  input="$(cat)"
  cmd="$(jq -r '.tool_input.command // ""' <<<"${input}")"

  if [[ -z "${cmd}" ]]; then
    exit 0
  fi

  check_path '~/.ssh' "${SSH_PATH}" "${cmd}"
  check_path '~/.aws' "${AWS_PATH}" "${cmd}"
  check_path '~/.gnupg' "${GNUPG_PATH}" "${cmd}"
  check_path '~/.kube' "${KUBE_PATH}" "${cmd}"
  check_path 'SSH private key' "${SSH_KEY_NAME}" "${cmd}"
  check_path '.env / .env.local' "${ENV_FILE}" "${cmd}"

  exit 0
}

main "$@"
