#!/bin/bash
#
# Report whether every settings variant satisfies the policy floor.
#
# This is the non-interactive half of the alignment sweep. It decides whether
# a sweep is needed and never performs one, because the merge asks a human a
# question whenever base and a variant disagree, and a script cannot ask.
# Performing the merge belongs to the update-claude-settings skill.
#
# It reports predicate names and violation paths. The floor predicate's
# violations carry values, and those values come from settings.base.json,
# which AuditBase precondition 3 requires to name nothing exempt, so they are
# policy rather than material.
#
# Usage: harness-align-check.sh
#
# The next line is a file-wide directive and must sit above the first
# command. It resolves the sourced library relative to this script.
# shellcheck source-path=SCRIPTDIR

set -o errexit
set -o nounset
set -o pipefail

readonly EXIT_DRIFTED=11

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

predicates_filter() {
  printf '%s/skills/update-claude-settings/references/predicates.jq\n' \
    "$(harness::plugin_root)"
}

#######################################
# Name every variant: the files matching the user-scope glob, minus base,
# minus every basename the registry lists under notAVariant, plus
# settings.json. Read from the glob rather than from a list, since a profile
# gets added or renamed without notice.
# Arguments:
#   $1: the config root.
#   $2: the base settings file.
# Outputs:
#   One absolute path per line, in lexical order.
#######################################
enumerate_variants() {
  local config="$1"
  local base="$2"
  local skip
  skip="$(jq -r '[ (.alignment.notAVariant // [])[] ] | join(" ")' -- "${base}")"
  local candidate name keep skipped
  while IFS= read -r candidate; do
    [[ -n "${candidate}" ]] || continue
    name="$(basename -- "${candidate}")"
    [[ "${name}" != "settings.base.json" ]] || continue
    keep=1
    for skipped in ${skip}; do
      [[ "${name}" != "${skipped}" ]] || keep=0
    done
    if ((keep == 1)); then
      printf '%s\n' "${candidate}"
    fi
  done < <(find "${config}" -maxdepth 1 \
    \( -name 'settings.json' -o -name 'settings.*.json' \) 2>/dev/null | sort)
}

#######################################
# Run one predicate mode and report it.
# Arguments:
#   $1: the mode name.
#   $2: the base settings file.
#   $3: the variant file.
# Returns:
#   0 when the predicate holds.
#######################################
run_predicate() {
  local mode="$1"
  local base="$2"
  local variant="$3"
  local filter result ok
  filter="$(predicates_filter)"
  # jq exits 2 on a missing file and still prints a result computed from what
  # it read, so the exit status gets read alongside "ok".
  if ! result="$(jq -s --arg mode "${mode}" -f "${filter}" -- "${base}" "${variant}")"; then
    harness::report fail "${mode}" "jq could not evaluate the predicate"
    return 1
  fi
  ok="$(printf '%s' "${result}" | jq -r '.ok')"
  if [[ "${ok}" == "true" ]]; then
    harness::report pass "${mode}" ""
    return 0
  fi
  harness::report fail "${mode}" \
    "$(printf '%s' "${result}" | jq -r '
        [ (.violations // [])[] | (.path // .entry // (.lists | tostring) // "?") ]
        | unique | join(" ")')"
  return 1
}

main() {
  harness::require_cmd jq find sort

  local config base filter failed=0
  config="$(harness::config_dir)"
  base="$(harness::base_file)"
  filter="$(predicates_filter)"

  [[ -f "${base}" ]] || harness::die 2 \
    "no settings.base.json under $(harness::tildify "${config}")"
  [[ -f "${filter}" ]] || harness::die 2 "the predicates filter is missing"

  printf '== audit-base\n'
  local audit
  audit="$(jq -s --arg mode audit-base -f "${filter}" -- "${base}" "${base}")" || true
  if [[ "$(printf '%s' "${audit}" | jq -r '.ok')" == "true" ]]; then
    harness::report pass "audit-base" "the floor is fit to propagate"
  else
    harness::report fail "audit-base" \
      "$(printf '%s' "${audit}" | jq -r '[ .checks[] | select(.ok == false) | .name ] | join(" ")')"
    printf 'The floor is unfit, so no variant gets swept. Fix base first.\n'
    exit "${EXIT_DRIFTED}"
  fi

  local variant mode
  local -a variants=()
  while IFS= read -r variant; do
    [[ -n "${variant}" ]] && variants+=("${variant}")
  done < <(enumerate_variants "${config}" "${base}")

  if ((${#variants[@]} == 0)); then
    printf 'no variants under %s\n' "$(harness::tildify "${config}")"
    return 0
  fi

  for variant in "${variants[@]}"; do
    printf '== %s\n' "$(basename -- "${variant}")"
    for mode in keys floor disjoint residue; do
      run_predicate "${mode}" "${base}" "${variant}" || failed=1
    done
  done

  if ((failed == 0)); then
    printf 'every variant satisfies the floor\n'
    return 0
  fi
  printf 'At least one variant drifted. The merge asks a human a question per\n'
  printf 'conflict, so run it through the update-claude-settings skill:\n'
  printf '  "align my settings"\n'
  return "${EXIT_DRIFTED}"
}

main "$@"
