#!/bin/bash
#
# PreToolUse hook for the Bash and Read tools.
#
# Reads the hook input JSON from stdin and refuses (permissionDecision:
# "deny") when the proposed call would read a file at a secret-shaped
# path. For Bash it inspects the shell command; for Read it inspects the
# target path. Both branches test the same pattern set, so the policy has
# one definition.
#
# The Bash branch mirrors the permissions.deny `Read(...)` rules so the
# Bash tool does not bypass them when the OS sandbox is disabled. The
# Read branch stands beside those rules rather than in place of them.
#
# Coverage is conservative:
#   - SSH/AWS/GnuPG/kube directory paths (under $HOME, ~, or /Users/<user>)
#   - SSH private key filenames (id_rsa, id_ed25519, id_ecdsa, id_dsa)
#   - .env, .env.local, .env.<name>.local
#   - the dotty private store (.dotfiles/shell/lib/private/), which holds
#     the exported API tokens
#
# Out of scope (because they false-positive too aggressively):
#   - bare "credentials" / "secrets" substrings, since too many legitimate
#     paths contain those words. The Read tool deny still applies for those.
#
# Globals: MODE, SUBJECT (set by main before the checks run).
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (deny is communicated via stdout, not exit code).

set -euo pipefail

# Commands that read file contents from a path argument or redirect.
readonly READ_CMDS='(cat|tac|less|more|head|tail|bat|xxd|od|strings|hexdump|grep|rg|ripgrep|sed|awk|jq|yq|nl|file|wc|md5sum|sha1sum|sha256sum|sha512sum|cksum|cp|mv|install|tar|zip|gzip|bzip2|xz|7z|openssl|base64|gpg|ssh-keygen|ssh-add)'

# Path patterns. Each is matched as an extended regex against either the
# command string or the Read target. Patterns are deliberately anchored to
# avoid bare-word false positives, and exclude `/` and whitespace so a
# pattern cannot run past one path into the next argument.
# Single quotes are intentional: this is a regex matching the
# literal characters `$HOME` in the user's bash command, not a
# variable to expand.
# shellcheck disable=SC2016
readonly DOTDIR_USERS_PREFIX='(\$HOME|~|/Users/[^/[:space:]]+)'
readonly SSH_PATH="${DOTDIR_USERS_PREFIX}/\.ssh/"
readonly AWS_PATH="${DOTDIR_USERS_PREFIX}/\.aws/"
readonly GNUPG_PATH="${DOTDIR_USERS_PREFIX}/\.gnupg/"
readonly KUBE_PATH="${DOTDIR_USERS_PREFIX}/\.kube/"
readonly SSH_KEY_NAME='\bid_(rsa|ed25519|ecdsa|dsa)\b'
readonly ENV_FILE='(^|[[:space:]/=])\.env(\.local|\.[^.[:space:]/]+\.local)?($|[[:space:]])'
readonly DOTFILES_PRIVATE='\.dotfiles/shell/lib/private/'

# Set by main() from the hook envelope, read by every check below.
MODE=''
SUBJECT=''

#######################################
# Emit a deny decision and exit.
# Globals:
#   MODE
# Arguments:
#   $1 - human label for the path pattern that matched.
#######################################
deny() {
  local label="$1" action reason
  if [[ "${MODE}" == "path" ]]; then
    action='Read would open'
  else
    action='command would read'
  fi
  reason="Refused: ${action} a secret-shaped path (${label}). If this is intentional, run it yourself."
  jq -nc --arg r "${reason}" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

#######################################
# Test whether a read-style command appears on the same logical line as a
# secret path pattern. Logical lines are split on the shell separators
# `|`, `;`, `&`, and newlines.
# Globals:
#   SUBJECT
# Arguments:
#   $1 - regex for the secret path
#######################################
read_cmd_hits_path() {
  local path_re="$1"
  rg -q "\b${READ_CMDS}\b[^|;&"$'\n'"]*${path_re}" <<<"${SUBJECT}"
}

#######################################
# Test whether a shell input redirect targets a secret path. Catches
# `cmd < path`, `cmd 0< path`, and similar.
# Globals:
#   SUBJECT
# Arguments:
#   $1 - regex for the secret path
#######################################
redirect_hits_path() {
  local path_re="$1"
  rg -q "[0-9]?<[[:space:]]*[^|;&"$'\n'"]*${path_re}" <<<"${SUBJECT}"
}

#######################################
# Test whether a Read target matches a secret path pattern.
# Globals:
#   SUBJECT
# Arguments:
#   $1 - regex for the secret path
#######################################
path_hits_pattern() {
  local path_re="$1"
  rg -q "${path_re}" <<<"${SUBJECT}"
}

#######################################
# Run the checks the active mode calls for. Denies on the first hit.
# Globals:
#   MODE
# Arguments:
#   $1 - human label for the deny message
#   $2 - regex for the secret path
#######################################
check_pattern() {
  local label="$1" path_re="$2"
  if [[ "${MODE}" == "path" ]]; then
    if path_hits_pattern "${path_re}"; then
      deny "${label}"
    fi
  elif read_cmd_hits_path "${path_re}" || redirect_hits_path "${path_re}"; then
    deny "${label}"
  fi
}

#######################################
# Test every pattern in the policy against the subject.
# Globals:
#   SUBJECT
# Arguments:
#   None
#######################################
check_every_pattern() {
  # The first arg is a display label shown in the deny message. The
  # tilde is intentional shorthand for the user, not a path to expand.
  # shellcheck disable=SC2088
  check_pattern '~/.ssh' "${SSH_PATH}"
  # shellcheck disable=SC2088
  check_pattern '~/.aws' "${AWS_PATH}"
  # shellcheck disable=SC2088
  check_pattern '~/.gnupg' "${GNUPG_PATH}"
  # shellcheck disable=SC2088
  check_pattern '~/.kube' "${KUBE_PATH}"
  check_pattern 'SSH private key' "${SSH_KEY_NAME}"
  check_pattern '.env / .env.local' "${ENV_FILE}"
  check_pattern 'dotty private store' "${DOTFILES_PRIVATE}"
}

main() {
  local input tool_name
  input="$(cat)"
  tool_name="$(jq -r '.tool_name // ""' <<<"${input}")"

  case "${tool_name}" in
  Bash)
    MODE='command'
    SUBJECT="$(jq -r '.tool_input.command // ""' <<<"${input}")"
    ;;
  Read)
    MODE='path'
    SUBJECT="$(jq -r '.tool_input.file_path // ""' <<<"${input}")"
    ;;
  *)
    exit 0
    ;;
  esac

  if [[ -z "${SUBJECT}" ]]; then
    exit 0
  fi

  check_every_pattern

  exit 0
}

main "$@"
