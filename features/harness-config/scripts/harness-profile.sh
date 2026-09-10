#!/bin/bash
#
# Define, validate, activate, and inspect provider profiles.
#
# A profile holds one provider's identity: its endpoint, its model pins, and
# the path to the helper that produces its credential. It never holds the
# credential itself, and it never holds policy.
#
# Profiles live in the plugin's persistent data directory rather than in the
# plugin, because a plugin update orphans the versioned cache and a user's
# profiles must survive that.
#
# Usage: harness-profile.sh <command> [name]
#   list              every profile, its description, and which is active
#   show NAME         a profile's key paths and its non-credential values
#   add NAME          write a new profile from the template
#   validate NAME     run both gates and the helper contract; --all for every one
#   use NAME          validate, then write the declared paths into settings.json
#   current           the active profile's name
#   remove NAME       delete a profile file
#
# The next line is a file-wide directive and must sit above the first
# command. It resolves the three sourced libraries relative to this script.
# shellcheck source-path=SCRIPTDIR

set -o errexit
set -o nounset
set -o pipefail

readonly EXIT_USAGE=1
readonly EXIT_NO_PROFILE=3
readonly EXIT_EXISTS=4
readonly EXIT_INVALID=5
readonly EXIT_NONE_ACTIVE=6

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck source=lib/validate.sh
source "${SCRIPT_DIR}/lib/validate.sh"
# shellcheck source=lib/activate.sh
source "${SCRIPT_DIR}/lib/activate.sh"

usage() {
  sed -n '5,22p' -- "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

active_name() {
  local pointer
  pointer="$(harness::active_file)"
  [[ -f "${pointer}" ]] || return 1
  local name
  name="$(<"${pointer}")"
  [[ -n "${name}" ]] || return 1
  printf '%s\n' "${name}"
}

cmd_list() {
  local dir active file name describe marker
  dir="$(harness::profiles_dir)"
  active="$(active_name || true)"
  if [[ ! -d "${dir}" ]]; then
    printf 'no profiles yet. Run harness-setup.sh, then harness-profile.sh add NAME\n'
    return 0
  fi
  shopt -s nullglob
  local files=("${dir}"/*.json)
  shopt -u nullglob
  if ((${#files[@]} == 0)); then
    printf 'no profiles yet. Run harness-profile.sh add NAME\n'
    return 0
  fi
  for file in "${files[@]}"; do
    name="$(basename -- "${file}" .json)"
    describe="$(jq -r '.describe // ""' -- "${file}" 2>/dev/null || printf 'unreadable')"
    if [[ "${name}" == "${active}" ]]; then
      marker='*'
    else
      marker=' '
    fi
    printf '%s %-16s %s\n' "${marker}" "${name}" "${describe}"
  done
}

cmd_show() {
  local name="$1"
  local file
  file="$(harness::profile_file "${name}")"
  [[ -f "${file}" ]] || harness::die "${EXIT_NO_PROFILE}" "no profile named '${name}'"
  printf 'name        %s\n' "$(jq -r '.name // ""' -- "${file}")"
  printf 'describe    %s\n' "$(jq -r '.describe // ""' -- "${file}")"
  printf 'file        %s\n' "$(harness::tildify "${file}")"
  printf 'declares\n'
  jq -r '[ (.settings // {}) | paths(scalars) | join(".") ] | sort[] | "            " + .' \
    -- "${file}"
  printf 'values      every declared value except apiKeyHelper, which prints as a path\n'
  jq -r '
    (.settings // {})
    | [ paths(scalars) as $p | { k: ($p | join(".")), v: getpath($p) } ]
    | sort_by(.k)[]
    | if (.k | test("(token|key|secret|password|credential)$"; "i"))
      then "            " + .k + " = <withheld>"
      else "            " + .k + " = " + (.v | tostring)
      end' -- "${file}"
  local helper
  helper="$(jq -r '.settings.apiKeyHelper // ""' -- "${file}")"
  if [[ -n "${helper}" ]]; then
    printf 'helper      %s\n' "$(harness::tildify "${helper/#\~/${HOME}}")"
  fi
}

cmd_add() {
  local name="$1"
  local file dir template
  dir="$(harness::profiles_dir)"
  file="$(harness::profile_file "${name}")"
  template="$(harness::plugin_root)/templates/profile.template.json"
  [[ ! -e "${file}" ]] || harness::die "${EXIT_EXISTS}" "a profile named '${name}' already exists"
  [[ -f "${template}" ]] || harness::die "${EXIT_INVALID}" "the profile template is missing"
  mkdir -p -- "${dir}"
  jq --arg name "${name}" '.name = $name' -- "${template}" >"${file}"
  # BSD chmod reads -- as a filename rather than as end-of-options, so it is
  # omitted here. Every path reaching chmod in this plugin is absolute, so it
  # cannot begin with a dash and be read as an option.
  chmod 600 "${file}"
  printf 'wrote %s\n' "$(harness::tildify "${file}")"
  printf 'Edit it, then run: harness-profile.sh validate %s\n' "${name}"
}

cmd_validate() {
  local name="$1"
  local file failed=0
  if [[ "${name}" == "--all" ]]; then
    shopt -s nullglob
    local files=("$(harness::profiles_dir)"/*.json)
    shopt -u nullglob
    for file in "${files[@]}"; do
      printf '== %s\n' "$(basename -- "${file}" .json)"
      harness::validate_profile "${file}" || failed=1
    done
    ((failed == 0)) || exit "${EXIT_INVALID}"
    return 0
  fi
  file="$(harness::profile_file "${name}")"
  [[ -f "${file}" ]] || harness::die "${EXIT_NO_PROFILE}" "no profile named '${name}'"
  harness::validate_profile "${file}" || exit "${EXIT_INVALID}"
}

cmd_use() {
  local name="$1"
  local file
  file="$(harness::profile_file "${name}")"
  [[ -f "${file}" ]] || harness::die "${EXIT_NO_PROFILE}" "no profile named '${name}'"
  harness::validate_profile "${file}" || harness::die "${EXIT_INVALID}" \
    "'${name}' failed validation, so nothing was written"
  harness::activate_profile "${file}" "${name}" || harness::die "${EXIT_INVALID}" \
    "activation failed"
  printf 'The switch lands on the next session. This one keeps what it started with.\n'
}

cmd_current() {
  local name
  name="$(active_name)" || harness::die "${EXIT_NONE_ACTIVE}" "no profile is active"
  printf '%s\n' "${name}"
}

cmd_remove() {
  local name="$1"
  local file
  file="$(harness::profile_file "${name}")"
  [[ -f "${file}" ]] || harness::die "${EXIT_NO_PROFILE}" "no profile named '${name}'"
  rm -- "${file}"
  printf 'removed %s\n' "$(harness::tildify "${file}")"
  if [[ "$(active_name || true)" == "${name}" ]]; then
    printf 'It was the active profile. settings.json still holds its values.\n'
    printf 'Run harness-profile.sh use OTHER to replace them.\n'
  fi
}

main() {
  harness::require_cmd jq date
  local command="${1:-}"
  case "${command}" in
  list) cmd_list ;;
  current) cmd_current ;;
  show | add | validate | use | remove)
    local name="${2:-}"
    [[ "${command}" == "validate" && "${name}" == "--all" ]] ||
      harness::require_legal_name "${name}" "${EXIT_USAGE}"
    "cmd_${command}" "${name}"
    ;;
  -h | --help | help | '') usage ;;
  *)
    harness::err "unknown command '${command}'"
    usage >&2
    exit "${EXIT_USAGE}"
    ;;
  esac
}

main "$@"
