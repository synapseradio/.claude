#!/bin/bash
#
# Diagnose a provider profile that is not taking effect.
#
# Every check here reports key paths, hashes, and file facts. None of them
# reports a settings value, so running this script cannot put a credential in
# a transcript. Where a comparison needs two values, it compares their
# SHA-256 digests and prints "match" or "differ": a digest of an endpoint is
# not the endpoint.
#
# Usage: harness-doctor.sh
#
# The next line is a file-wide directive and must sit above the first
# command. It resolves the sourced library relative to this script.
# shellcheck source-path=SCRIPTDIR

set -o errexit
set -o nounset
set -o pipefail

readonly EXIT_UNHEALTHY=7

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

#######################################
# Digest one JSON leaf so two of them can be compared without either being
# printed. Reads the value through jq and pipes it straight into shasum, so
# the value never lands in a shell variable.
# Arguments:
#   $1: the JSON file.
#   $2: a jq path expression, such as '.env.ANTHROPIC_BASE_URL'.
# Outputs:
#   Twelve hex characters, or "absent".
#######################################
digest_leaf() {
  local file="$1"
  local expr="$2"
  local raw
  raw="$(jq -r "${expr} // \"\"" -- "${file}" 2>/dev/null || printf '')"
  if [[ -z "${raw}" ]]; then
    printf 'absent\n'
    return 0
  fi
  printf '%s' "${raw}" | shasum -a 256 | cut -c1-12
}

#######################################
# Report which of a profile's declared paths settings.json now sets, by
# comparing two key-path sets. Neither set carries a value.
# Arguments:
#   $1: the settings file.
#   $2: the profile's declared paths, one per line, already sorted.
#######################################
report_paths() {
  local settings="$1"
  local declared="$2"
  local live missing
  live="$(harness::key_paths "${settings}")"
  missing="$(comm -23 <(printf '%s\n' "${declared}") <(printf '%s\n' "${live}" | sort))"
  if [[ -z "${missing}" ]]; then
    harness::report pass "declared-paths-present" \
      "settings.json sets every path the profile declares"
    return 0
  fi
  printf '%s\n' "${missing}"
  harness::report fail "declared-paths-present" "the paths above are missing"
  return 1
}

#######################################
# Compare each declared leaf by digest, so a stale value shows up without
# either value being printed.
# Arguments:
#   $1: the profile file.
#   $2: the settings file.
#   $3: the profile's declared paths, one per line, already sorted.
#######################################
report_values() {
  local profile="$1"
  local settings="$2"
  local declared="$3"
  local path expr from_profile from_settings failed=0
  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    # A dotted path becomes a bracketed jq expression, so a key holding a
    # character jq would read as syntax still resolves.
    expr=".[\"${path//./\"][\"}\"]"
    from_profile="$(digest_leaf "${profile}" ".settings${expr}")"
    from_settings="$(digest_leaf "${settings}" "${expr}")"
    if [[ "${from_profile}" == "${from_settings}" ]]; then
      harness::report pass "value-matches" "${path}"
    else
      harness::report fail "value-matches" \
        "${path}: profile ${from_profile}, settings.json ${from_settings}"
      failed=1
    fi
  done <<<"${declared}"
  return "${failed}"
}

main() {
  harness::require_cmd jq shasum comm sort

  local config settings pointer name profile failed=0
  config="$(harness::config_dir)"
  settings="$(harness::settings_file)"
  pointer="$(harness::active_file)"

  harness::report note "config-root" "$(harness::tildify "${config}")"
  harness::report note "data-root" "$(harness::tildify "$(harness::data_dir)")"

  if [[ -f "${settings}" ]]; then
    harness::report pass "settings-json-exists" ""
  else
    harness::report fail "settings-json-exists" \
      "no settings.json under the config root, so no profile can be in effect"
    exit "${EXIT_UNHEALTHY}"
  fi

  if jq -e . -- "${settings}" >/dev/null 2>&1; then
    harness::report pass "settings-json-parses" ""
  else
    harness::report fail "settings-json-parses" \
      "malformed JSON silently disables every setting in the file"
    exit "${EXIT_UNHEALTHY}"
  fi

  if [[ -f "${pointer}" ]]; then
    name="$(<"${pointer}")"
  else
    name=""
  fi
  if [[ -z "${name}" ]]; then
    harness::report fail "a-profile-is-active" \
      "no active pointer; run harness-profile.sh use NAME"
    exit "${EXIT_UNHEALTHY}"
  fi
  harness::report pass "a-profile-is-active" "${name}"

  profile="$(harness::profile_file "${name}")"
  if [[ -f "${profile}" ]]; then
    harness::report pass "active-profile-exists" ""
  else
    harness::report fail "active-profile-exists" \
      "the pointer names '${name}' and no such profile file exists"
    exit "${EXIT_UNHEALTHY}"
  fi

  local declared
  declared="$(jq -r '[ (.settings // {}) | paths(scalars) | join(".") ] | sort | .[]' \
    -- "${profile}")"
  report_paths "${settings}" "${declared}" || failed=1
  report_values "${profile}" "${settings}" "${declared}" || failed=1

  # A variant file left over from before the plugin still overrides nothing by
  # itself, and the CLI never reads it. Naming it here saves the next reader
  # the search.
  local -a variants=()
  local candidate
  while IFS= read -r candidate; do
    [[ -n "${candidate}" ]] && variants+=("$(basename -- "${candidate}")")
  done < <(find "${config}" -maxdepth 1 -name 'settings.*.json' \
    -not -name 'settings.base.json' 2>/dev/null || true)
  if ((${#variants[@]} > 0)); then
    harness::report note "legacy-variants-present" "${variants[*]}"
    harness::report note "legacy-variants-inert" \
      "the CLI reads settings.json alone at user scope, so these change nothing until copied"
  fi

  if ((failed == 0)); then
    printf 'The active profile is fully in effect in settings.json.\n'
    printf 'A session started before the last switch still holds the old values.\n'
    return 0
  fi
  printf 'Run harness-profile.sh use %s to rewrite the declared paths.\n' "${name}"
  return "${EXIT_UNHEALTHY}"
}

main "$@"
