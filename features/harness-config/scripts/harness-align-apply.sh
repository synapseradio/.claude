#!/bin/bash
#
# Merge the policy floor into every settings variant, or stop at the first
# question only a human answers.
#
# This is the mechanical half of the alignment sweep: the Reconcile machine's
# Acquire, AuditBase, Survey, Project, Seal, Apply, Verify, and Resurvey
# states, run by jq with no model reading a variant. Every fork the machine
# would hand to Consult comes back as a conflict, and a variant with one is
# left untouched and named, so the update-claude-settings skill can put the
# question to a person with only the path in hand.
#
# Output names paths, verdicts, and counts. It never carries a settings
# value, because a variant may hold a credential and this script's transcript
# reaches a model.
#
# Usage: harness-align-apply.sh [--dry-run] [--variant NAME]...
#   --dry-run        report every write and perform none
#   --variant NAME   sweep only the variant with this basename; repeatable
#
# Exit status:
#   0   every swept variant is aligned, written or already sealed
#   11  the floor failed its audit and nothing was swept
#   13  at least one variant holds a conflict and was left untouched
#   14  a write failed verification and the backup was restored
#
# The next line is a file-wide directive and must sit above the first
# command. It resolves the sourced library relative to this script.
# shellcheck source-path=SCRIPTDIR

set -o errexit
set -o nounset
set -o pipefail

readonly EXIT_USAGE=1
readonly EXIT_UNFIT=11
readonly EXIT_CONSULT=13
readonly EXIT_REVERTED=14

# The verdicts that change a file. The rest (satisfied, variant-only,
# exempt) describe what the merge left as it was.
readonly ACTING_VERDICTS='["add", "corrected", "collapsed", "removed"]'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

DRY_RUN=0
declare -a ONLY_VARIANTS=()

usage() {
  sed -n '17,26p' -- "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

#######################################
# Print the merge ledger for one variant: every conflict, then every acting
# verdict with its count.
# Arguments:
#   $1: the ledger file the merge mode wrote.
# Outputs:
#   One line per conflict and per acting verdict on STDOUT.
#######################################
print_ledger() {
  local ledger="$1"
  local line
  while IFS= read -r line; do
    [[ -n "${line}" ]] || continue
    printf '  %s\n' "${line}"
  done < <(jq -r --argjson acting "${ACTING_VERDICTS}" '
      (.conflicts[] | "conflict   \(.kind)  \(.path)"),
      (.actions[] | select(.verdict | IN($acting[]))
        | "\(.verdict | . + "          " | .[0:10]) \(.path)"
          + (if .count > 1 then "  (\(.count) members)" else "" end))
    ' -- "${ledger}")
}

#######################################
# Fail unless every alignment predicate holds for a written variant and a
# second merge finds nothing left to do. The second merge's result must also
# be byte-identical to the file, which is what proves the seal is stable.
# Arguments:
#   $1: the base settings file.
#   $2: the variant file, already written.
#   $3: a scratch directory.
# Returns:
#   0 when the variant is sealed and aligned.
#######################################
verify_written() {
  local base="$1"
  local variant="$2"
  local scratch="$3"
  local mode failed=0
  for mode in keys floor disjoint residue; do
    harness::run_predicate "${mode}" "${base}" "${variant}" || failed=1
  done
  ((failed == 0)) || return 1

  local resurvey="${scratch}/resurvey.json"
  if ! jq -s --arg mode merge -f "$(harness::predicates_filter)" -- "${base}" "${variant}" >"${resurvey}"; then
    harness::report fail "resurvey" "jq could not evaluate the second merge"
    return 1
  fi
  local pending
  pending="$(jq -r --argjson acting "${ACTING_VERDICTS}" '
      (.conflicts | length) + ([ .actions[] | select(.verdict | IN($acting[])) ] | length)
    ' -- "${resurvey}")"
  if [[ "${pending}" != "0" ]]; then
    harness::report fail "resurvey" "a second merge still finds work to do"
    return 1
  fi
  jq '.result' -- "${resurvey}" >"${scratch}/resealed.json"
  if ! cmp -s "${scratch}/resealed.json" "${variant}"; then
    harness::report fail "resurvey" "a second seal differs from the written file"
    return 1
  fi
  harness::report pass "resurvey" "idempotent"
  return 0
}

#######################################
# Run the machine over one variant.
# Globals:
#   DRY_RUN
# Arguments:
#   $1: the base settings file.
#   $2: the variant file.
#   $3: a scratch directory.
# Returns:
#   0 aligned, EXIT_CONSULT on a conflict, EXIT_REVERTED on a failed write.
#######################################
sweep_variant() {
  local base="$1"
  local variant="$2"
  local scratch="$3"
  local name
  name="$(basename -- "${variant}")"
  printf '== %s\n' "${name}"

  local ledger="${scratch}/ledger.json"
  if ! jq -s --arg mode merge -f "$(harness::predicates_filter)" -- "${base}" "${variant}" >"${ledger}"; then
    harness::report fail "merge" "jq could not evaluate the merge"
    return "${EXIT_CONSULT}"
  fi
  print_ledger "${ledger}"

  local conflicts
  conflicts="$(jq -r '.conflicts | length' -- "${ledger}")"
  if [[ "${conflicts}" != "0" ]]; then
    harness::report fail "consult" "${conflicts} conflict(s) above need a human; nothing written"
    return "${EXIT_CONSULT}"
  fi

  # Seal: jq's own serialization is the byte-stable form the machine names.
  local sealed="${variant}.harness-tmp"
  jq '.result' -- "${ledger}" >"${sealed}"
  if cmp -s "${sealed}" "${variant}"; then
    rm -f -- "${sealed}"
    harness::report pass "aligned" "already sealed"
    return 0
  fi

  if ((DRY_RUN)); then
    rm -f -- "${sealed}"
    harness::report pass "would-write" "dry run"
    return 0
  fi

  local backups backup mode
  backups="$(harness::backups_dir)"
  mkdir -p -- "${backups}"
  backup="${backups}/${name}.pre-$(date -u +%Y%m%dT%H%M%SZ).json"
  cp -p -- "${variant}" "${backup}"
  # macOS chmod rejects a "--" separator, and the path is built here, so it
  # never begins with a dash.
  if mode="$(harness::file_mode "${variant}")"; then
    chmod "${mode}" "${sealed}"
  fi
  mv -f -- "${sealed}" "${variant}"

  if verify_written "${base}" "${variant}" "${scratch}"; then
    harness::report pass "written" "backup $(harness::tildify "${backup}")"
    return 0
  fi
  cp -p -- "${backup}" "${variant}"
  harness::report fail "reverted" "restored from $(harness::tildify "${backup}")"
  return "${EXIT_REVERTED}"
}

#######################################
# Fail unless the variant's basename is among the names the caller asked
# for, or the caller asked for none.
# Globals:
#   ONLY_VARIANTS
# Arguments:
#   $1: the variant file.
#######################################
wanted() {
  local variant="$1"
  ((${#ONLY_VARIANTS[@]} > 0)) || return 0
  local name only
  name="$(basename -- "${variant}")"
  for only in "${ONLY_VARIANTS[@]}"; do
    [[ "${name}" != "${only}" ]] || return 0
  done
  return 1
}

parse_args() {
  while (($# > 0)); do
    case "$1" in
      --dry-run) DRY_RUN=1 ;;
      --variant)
        [[ -n "${2:-}" ]] || harness::die "${EXIT_USAGE}" "--variant needs a basename"
        ONLY_VARIANTS+=("$2")
        shift
        ;;
      -h | --help | help) usage; exit 0 ;;
      *)
        harness::err "unknown argument '$1'"
        usage >&2
        exit "${EXIT_USAGE}"
        ;;
    esac
    shift
  done
}

main() {
  parse_args "$@"
  harness::require_cmd jq find sort cmp

  local config base filter
  config="$(harness::config_dir)"
  base="$(harness::base_file)"
  filter="$(harness::predicates_filter)"

  [[ -f "${base}" ]] || harness::die 2 \
    "no settings.base.json under $(harness::tildify "${config}")"
  [[ -f "${filter}" ]] || harness::die 2 "the predicates filter is missing"

  printf '== audit-base\n'
  if ! harness::audit_base "${base}"; then
    printf 'The floor is unfit, so no variant gets swept. Fix base first.\n'
    exit "${EXIT_UNFIT}"
  fi

  # Scratch lives under the data directory, which the deny rules cover, so
  # a ledger holding the merged document is never readable by a model even
  # for the moment it exists. The EXIT trap fires after main returns, so the
  # path it removes is a global rather than a local.
  mkdir -p -- "$(harness::data_dir)"
  SCRATCH="$(mktemp -d "$(harness::data_dir)/.align-apply.XXXXXX")"
  readonly SCRATCH
  trap 'rm -rf -- "${SCRATCH}"' EXIT
  local scratch="${SCRATCH}"

  local variant status worst=0
  local -a variants=()
  while IFS= read -r variant; do
    [[ -n "${variant}" ]] || continue
    wanted "${variant}" && variants+=("${variant}")
  done < <(harness::variants "${config}" "${base}")

  if ((${#variants[@]} == 0)); then
    printf 'no variants under %s\n' "$(harness::tildify "${config}")"
    return 0
  fi

  for variant in "${variants[@]}"; do
    status=0
    sweep_variant "${base}" "${variant}" "${scratch}" || status=$?
    ((status <= worst)) || worst="${status}"
  done

  if ((worst == 0)); then
    printf 'every swept variant is aligned\n'
    return 0
  fi
  if ((worst == EXIT_CONSULT)); then
    printf 'A variant above holds a conflict. Each one is a question for a person;\n'
    printf 'put it through the update-claude-settings skill with the path in hand.\n'
  fi
  return "${worst}"
}

main "$@"
