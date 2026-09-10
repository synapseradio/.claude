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
# A deny rule on the Read tool does not cover this, because the Bash tool
# opens a file without going through Read. This guard closes that route.
#
# Coverage is conservative, and every pattern below holds on any machine:
#   - SSH/AWS/GnuPG/kube directory paths, whether written under $HOME, ~,
#     or an absolute home directory on either macOS or Linux
#   - SSH private key filenames (id_rsa, id_ed25519, id_ecdsa, id_dsa)
#   - .env, .env.local, .env.<name>.local
#   - a private/ directory inside a dotfiles checkout, the usual home of
#     shell functions that export keys
#   - a file named to be sourced for its secrets: secrets.env, secrets.sh
#     and its shell variants, anything.secrets, and a .secrets directory
#
# Two shapes stay out of the set that ships, and neither is forbidden. A
# user turns either on in the banned-reads file described below.
#   - a bare "credentials" or "secrets" substring, which appears in too
#     many ordinary paths to deny for everyone
#   - a bare private/ segment, which would deny /private/tmp and
#     /private/var, the real /tmp and /var on macOS. The dotfiles
#     component is what makes the shipped pattern safe to hold.
#
# One shape no pattern here reaches: the file an apiKeyHelper reads. That
# file answers to no naming convention, and any pattern wide enough to find
# it by name also denies ~/.ssh/known_hosts, a keyboard layout, or a
# keychain export. Where such a helper sits in a dotfiles private/ store or
# carries a secrets name, the patterns above catch it. Otherwise a user
# names it in the banned-reads file, and the README says so plainly.
#
# Nothing here names a directory particular to one person's machine.
#
# Globals: MODE, SUBJECT (set by main before the checks run).
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (deny is communicated via stdout, not exit code).

# The check_every_pattern labels below spell a few directories with a
# leading tilde, intentional shorthand for the user's home directory in a
# display string, not a path shellcheck should try to expand.
# shellcheck disable=SC2088
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
readonly DOTDIR_USERS_PREFIX='(\$HOME|~|/(Users|home|root)/[^/[:space:]]+)'
readonly SSH_PATH="${DOTDIR_USERS_PREFIX}/\.ssh/"
readonly AWS_PATH="${DOTDIR_USERS_PREFIX}/\.aws/"
readonly GNUPG_PATH="${DOTDIR_USERS_PREFIX}/\.gnupg/"
readonly KUBE_PATH="${DOTDIR_USERS_PREFIX}/\.kube/"
readonly SSH_KEY_NAME='\bid_(rsa|ed25519|ecdsa|dsa)\b'
readonly ENV_FILE='(^|[[:space:]/=])\.env(\.local|\.[^.[:space:]/]+\.local)?($|[[:space:]])'

# A private/ directory inside a dotfiles checkout. The dotfiles component
# is what anchors this: a bare private/ would deny /private/tmp and
# /private/var, and docs/private/ in any project.
readonly DOTFILES_PRIVATE='\.?dotfiles/([^[:space:]"]*/)?private/'

# A file named to be sourced for the secrets it holds, taken as a whole
# filename at both ends. rotate-secrets.sh, secrets.env.example, and
# .secrets.baseline all fall outside it and stay readable.
readonly SECRETS_FILE='(^|[[:space:]/=])(secrets\.(sh|bash|zsh|env)|[^[:space:]/=]*\.secrets)($|[[:space:]])'
readonly SECRETS_DIR='(^|[[:space:]/=])\.secrets/'

# The OR of the nine raw path patterns above, with none of the READ_CMDS or
# redirect wrapping that check_pattern adds. Every wrapped check requires
# its own path_re to match somewhere in the subject as a precondition, so a
# miss here proves none of the nine wrapped checks can fire, and the loop
# below can be skipped. None of the nine patterns leaks a bare top-level
# alternation, so joining them with `|` composes safely.
readonly ALL_PATH_PATTERNS="${SSH_PATH}|${AWS_PATH}|${GNUPG_PATH}|${KUBE_PATH}|${SSH_KEY_NAME}|${ENV_FILE}|${DOTFILES_PRIVATE}|${SECRETS_FILE}|${SECRETS_DIR}"

# Whatever else a user wants refused lives in a file in their own Claude
# directory, one fragment of a path or filename per line, with blank lines
# and # comments skipped. Each line is matched literally, so a line needs
# no escaping and cannot misfire as a regex. This is where a word too broad
# to ship for everyone, "credentials" among them, becomes a denial for the
# person who chose it.
#
# The location comes from BASH_GUARDS_BANNED_READS, else the user Claude
# directory: $CLAUDE_CONFIG_DIR/bash-guards/banned-reads.conf, else
# ~/.claude/bash-guards/banned-reads.conf.
#
# The file only adds. A line in it joins the patterns above and can never
# remove one, so a file that is missing, empty, or truncated leaves every
# default in force.
readonly BANNED_READS_LEAF='bash-guards/banned-reads.conf'

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
# Test every pattern in the policy against the subject. The nine built-in
# patterns run behind one combined pre-check: when none of their raw path
# regexes appears anywhere in the subject, no wrapped check (which only
# adds a READ_CMDS or redirect precondition on top of the same raw regex)
# can fire either, so the whole loop is skipped. The banned-reads check
# always runs: its patterns come from a user file at runtime and are not
# part of the combined regex.
# Globals:
#   SUBJECT, ALL_PATH_PATTERNS
# Arguments:
#   None
#######################################
check_every_pattern() {
  if rg -q "${ALL_PATH_PATTERNS}" <<<"${SUBJECT}"; then
    # The first arg to each call below is a display label shown in the deny
    # message; see the file-level SC2088 disable above for the leading
    # tildes.
    check_pattern '~/.ssh' "${SSH_PATH}"
    check_pattern '~/.aws' "${AWS_PATH}"
    check_pattern '~/.gnupg' "${GNUPG_PATH}"
    check_pattern '~/.kube' "${KUBE_PATH}"
    check_pattern 'SSH private key' "${SSH_KEY_NAME}"
    check_pattern '.env / .env.local' "${ENV_FILE}"
    check_pattern 'private store in a dotfiles checkout' "${DOTFILES_PRIVATE}"
    check_pattern 'a file named for the secrets it holds' "${SECRETS_FILE}"
    check_pattern '.secrets directory' "${SECRETS_DIR}"
  fi
  check_banned_reads
}

#######################################
# Report the banned-reads file's location.
# Globals:
#   BASH_GUARDS_BANNED_READS, CLAUDE_CONFIG_DIR, HOME, BANNED_READS_LEAF
# Outputs:
#   The path on stdout.
#######################################
banned_reads_file() {
  if [[ -n "${BASH_GUARDS_BANNED_READS:-}" ]]; then
    printf '%s\n' "${BASH_GUARDS_BANNED_READS}"
    return 0
  fi
  printf '%s/%s\n' "${CLAUDE_CONFIG_DIR:-${HOME}/.claude}" \
    "${BANNED_READS_LEAF}"
}

#######################################
# Escape every regex metacharacter in a string, so a line from the user's
# file matches the characters they wrote and nothing else.
# Arguments:
#   $1 - the literal text.
# Outputs:
#   The escaped text on stdout.
#######################################
escape_regex() {
  local text="$1" out='' char index
  for ((index = 0; index < ${#text}; index++)); do
    char="${text:index:1}"
    case "${char}" in
    [\\^\$.\[\]\|\(\)\*\+\?\{\}]) out+="\\${char}" ;;
    *) out+="${char}" ;;
    esac
  done
  printf '%s\n' "${out}"
}

#######################################
# Test each fragment the user banned against the subject.
# Globals:
#   SUBJECT
# Arguments:
#   None
#######################################
check_banned_reads() {
  local file line
  file="$(banned_reads_file)"
  [[ -r "${file}" ]] || return 0

  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line%%#*}"
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -n "${line}" ]] || continue
    check_pattern "a fragment you banned in ${file}" "$(escape_regex "${line}")"
  done <"${file}"
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
