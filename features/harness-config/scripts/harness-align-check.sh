#!/bin/bash
#
# Report whether every settings variant satisfies the policy floor.
#
# This is the read-only half of the alignment sweep. It decides whether a
# sweep is needed and performs none. harness-align-apply.sh performs the
# mechanical part of one and halts at every fork that needs a human, so the
# update-claude-settings skill is where those forks get answered.
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

main() {
  harness::require_cmd jq find sort

  local config base filter failed=0
  config="$(harness::config_dir)"
  base="$(harness::base_file)"
  filter="$(harness::predicates_filter)"

  [[ -f "${base}" ]] || harness::die 2 \
    "no settings.base.json under $(harness::tildify "${config}")"
  [[ -f "${filter}" ]] || harness::die 2 "the predicates filter is missing"

  printf '== audit-base\n'
  if ! harness::audit_base "${base}"; then
    printf 'The floor is unfit, so no variant gets swept. Fix base first.\n'
    exit "${EXIT_DRIFTED}"
  fi

  local variant mode
  local -a variants=()
  while IFS= read -r variant; do
    [[ -n "${variant}" ]] && variants+=("${variant}")
  done < <(harness::variants "${config}" "${base}")

  if ((${#variants[@]} == 0)); then
    printf 'no variants under %s\n' "$(harness::tildify "${config}")"
    return 0
  fi

  for variant in "${variants[@]}"; do
    printf '== %s\n' "$(basename -- "${variant}")"
    for mode in keys floor disjoint residue; do
      harness::run_predicate "${mode}" "${base}" "${variant}" || failed=1
    done
  done

  if ((failed == 0)); then
    printf 'every variant satisfies the floor\n'
    return 0
  fi
  printf 'At least one variant drifted. Run the mechanical merge, which halts\n'
  printf 'at every fork that needs a human:\n'
  printf '  %s/harness-align-apply.sh --dry-run\n' "$(harness::tildify "${SCRIPT_DIR}")"
  return "${EXIT_DRIFTED}"
}

main "$@"
