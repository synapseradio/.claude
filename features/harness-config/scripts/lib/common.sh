# shellcheck shell=bash
#
# Shared path resolution and reporting for the harness-config scripts.
#
# Source this file; never execute it. Every directory it resolves reads an
# override first, so a test exports the override to a temporary directory and
# the scripts under test have no path to real user state.
#
# Globals this library reads:
#   CLAUDE_CONFIG_DIR    the config root, default "${HOME}/.claude"
#   CLAUDE_PLUGIN_DATA   the harness-set persistent data directory
#   CLAUDE_PLUGIN_ROOT   the harness-set plugin directory
#   HARNESS_CONFIG_DATA  a test's override for the data directory
#   HOME                 the fallback for the config root

if [[ -n "${HARNESS_COMMON_SOURCED:-}" ]]; then
  return 0
fi
HARNESS_COMMON_SOURCED=1

# A profile name reaches a filename and a settings-variant name, so it takes
# the narrower of the two alphabets. The credential-shape patterns live in
# scripts/lib/profile-gates.jq, which is where the gates that use them run.
HARNESS_NAME_RE='^[a-z0-9][a-z0-9-]*$'

# Two names would collide with a settings file that is not a variant.
HARNESS_RESERVED_NAMES='base local'

#######################################
# Write a timestamped message to stderr.
# Arguments:
#   The message, as one or more words.
# Outputs:
#   The message on STDERR.
#######################################
harness::err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}

#######################################
# Write a message to stderr and exit.
# Arguments:
#   $1: the exit status.
#   The rest: the message.
#######################################
harness::die() {
  local status="$1"
  shift
  harness::err "$@"
  exit "${status}"
}

#######################################
# Resolve the config root.
# Globals:
#   CLAUDE_CONFIG_DIR, HOME
# Outputs:
#   The directory path on STDOUT.
#######################################
harness::config_dir() {
  printf '%s\n' "${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"
}

#######################################
# Resolve the plugin's persistent data directory. The harness sets
# CLAUDE_PLUGIN_DATA for a plugin hook, and a skill's Bash call may not carry
# it, so the fallback derives the documented location. Anything a user owns
# lives here, because the versioned plugin cache is orphaned on update.
# Globals:
#   HARNESS_CONFIG_DATA, CLAUDE_PLUGIN_DATA
# Outputs:
#   The directory path on STDOUT.
#######################################
harness::data_dir() {
  if [[ -n "${HARNESS_CONFIG_DATA:-}" ]]; then
    printf '%s\n' "${HARNESS_CONFIG_DATA}"
    return 0
  fi
  if [[ -n "${CLAUDE_PLUGIN_DATA:-}" ]]; then
    printf '%s\n' "${CLAUDE_PLUGIN_DATA}"
    return 0
  fi
  printf '%s/plugins/data/harness-config\n' "$(harness::config_dir)"
}

#######################################
# Resolve the plugin root. A script invoked by absolute path finds its own
# siblings without the harness setting anything.
# Globals:
#   CLAUDE_PLUGIN_ROOT, BASH_SOURCE
# Outputs:
#   The directory path on STDOUT.
#######################################
harness::plugin_root() {
  if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
    printf '%s\n' "${CLAUDE_PLUGIN_ROOT}"
    return 0
  fi
  local lib_dir
  lib_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  printf '%s\n' "${lib_dir%/scripts/lib}"
}

harness::profiles_dir() {
  printf '%s/profiles\n' "$(harness::data_dir)"
}

harness::active_file() {
  printf '%s/active\n' "$(harness::data_dir)"
}

harness::profile_file() {
  printf '%s/%s.json\n' "$(harness::profiles_dir)" "$1"
}

harness::settings_file() {
  printf '%s/settings.json\n' "$(harness::config_dir)"
}

harness::base_file() {
  printf '%s/settings.base.json\n' "$(harness::config_dir)"
}

harness::gates_filter() {
  printf '%s/scripts/lib/profile-gates.jq\n' "$(harness::plugin_root)"
}

#######################################
# Rewrite a leading home directory as a tilde, which removes the account
# identifier from anything printed. Every command that prints a filesystem
# path passes it through here first, so no account name reaches a transcript.
# Globals:
#   HOME
# Arguments:
#   $1: the path.
# Outputs:
#   The rewritten path on STDOUT.
#######################################
harness::tildify() {
  local path="$1"
  if [[ -n "${HOME:-}" && "${path}" == "${HOME}"/* ]]; then
    printf '%s/%s\n' '~' "${path#"${HOME}"/}"
    return 0
  fi
  printf '%s\n' "${path}"
}

#######################################
# Fail unless a name is a legal profile name. The name reaches a filename, so
# rejecting a slash or a dot here is what keeps a profile inside its
# directory.
# Globals:
#   HARNESS_NAME_RE, HARNESS_RESERVED_NAMES
# Arguments:
#   $1: the candidate name.
#   $2: the exit status to die with.
#######################################
harness::require_legal_name() {
  local name="${1:-}"
  local status="${2:-1}"
  local reserved
  [[ -n "${name}" ]] || harness::die "${status}" "this command needs a profile name"
  [[ "${name}" =~ ${HARNESS_NAME_RE} ]] ||
    harness::die "${status}" "a profile name matches ${HARNESS_NAME_RE}; got '${name}'"
  for reserved in ${HARNESS_RESERVED_NAMES}; do
    [[ "${name}" != "${reserved}" ]] ||
      harness::die "${status}" "'${name}' names a settings file that is not a variant"
  done
}

#######################################
# Report a file's permission bits as three or four octal digits. macOS and
# GNU coreutils disagree on the flag, so this tries one and falls back.
# Arguments:
#   $1: the path.
# Outputs:
#   The octal mode on STDOUT, or nothing when the file is unreadable.
#######################################
harness::file_mode() {
  local path="$1"
  stat -f '%OLp' -- "${path}" 2>/dev/null && return 0
  stat -c '%a' -- "${path}" 2>/dev/null && return 0
  return 1
}

#######################################
# Report a settings file's key paths and no value. This is the only shape in
# which any diagnostic here inspects a file that may hold a credential.
# Arguments:
#   $1: the path to a JSON file.
# Outputs:
#   One dotted key path per line on STDOUT.
#######################################
harness::key_paths() {
  local path="$1"
  [[ -f "${path}" ]] || return 1
  jq -r 'paths(scalars) | map(select(type == "string")) | join(".")' -- "${path}"
}

#######################################
# Run each "name:pattern" check against one or more directories with
# grep -rlE, reporting one pass or fail line per check. Every guard
# subcommand that scans a tree for a shape repeats this loop with only its
# directories and grep-scoping flags differing (an include list, an
# exclude list, or both), so this holds the loop and lets each caller
# supply just its scope and checks.
#
# A nameref (local -n) would let the checks live in the caller's own array
# and read more directly here, but this plugin's scripts run under the
# bash each one's shebang names, which on macOS is the system /bin/bash,
# still 3.2; nameref did not exist before 4.3. Two literal "--" separate
# the directories, this function's own grep-flag arguments, and the check
# entries instead.
# Arguments:
#   Up to the first literal "--": one or more directories to scan.
#   Between the two "--": grep flags that scope the scan.
#   After the second "--": one or more "name:pattern" check entries.
# Outputs:
#   Each matching file's path, then one report line per check.
# Returns:
#   0 when every check passes.
#######################################
harness::scan_checks() {
  local -a dirs=()
  while [[ "$#" -gt 0 && "$1" != "--" ]]; do
    dirs+=("$1")
    shift
  done
  shift # drop the first --
  local -a grep_args=()
  while [[ "$#" -gt 0 && "$1" != "--" ]]; do
    grep_args+=("$1")
    shift
  done
  shift # drop the second --
  local failed=0 entry name pattern hits
  for entry in "$@"; do
    name="${entry%%:*}"
    pattern="${entry#*:}"
    hits="$(grep -rlE "${grep_args[@]}" -e "${pattern}" -- "${dirs[@]}" || true)"
    if [[ -n "${hits}" ]]; then
      printf '%s\n' "${hits}"
      harness::report fail "${name}" "$(printf '%s\n' "${hits}" | wc -l | tr -d ' ') file(s) above"
      failed=1
    else
      harness::report pass "${name}" ""
    fi
  done
  return "${failed}"
}

#######################################
# Fail unless every named command is on PATH.
# Arguments:
#   The command names.
#######################################
harness::require_cmd() {
  local name
  local missing=()
  for name in "$@"; do
    command -v -- "${name}" >/dev/null 2>&1 || missing+=("${name}")
  done
  if ((${#missing[@]} > 0)); then
    harness::die 2 "missing required commands: ${missing[*]}"
  fi
}

#######################################
# Print one check result in a fixed two-column form a reader scans.
# Arguments:
#   $1: "pass" or "fail".
#   $2: the check name.
#   The rest: the detail, which never carries a settings value.
#######################################
harness::report() {
  local outcome="$1"
  local name="$2"
  shift 2
  printf '%-4s  %-34s  %s\n' "${outcome}" "${name}" "$*"
}
