# shellcheck shell=bash
#
# Profile validation: the two gates, and the apiKeyHelper contract.
#
# Source this file; never execute it. It expects lib/common.sh sourced first.
#
# Nothing here executes an apiKeyHelper. Running one produces a credential on
# stdout, and whatever ran it then holds the credential in a variable, a
# process, and a transcript. The contract below proves a helper is installed
# and never that it works.

if [[ -n "${HARNESS_VALIDATE_SOURCED:-}" ]]; then
  return 0
fi
HARNESS_VALIDATE_SOURCED=1

#######################################
# Run the shape, exempt-bound, and credential gates against one profile.
# Arguments:
#   $1: the profile file.
# Outputs:
#   One report line per gate on STDOUT, and the failing gate names on STDERR.
# Returns:
#   0 when every gate passes, 1 otherwise.
#######################################
harness::gates() {
  local profile="$1"
  local base gates result
  base="$(harness::base_file)"
  gates="$(harness::gates_filter)"

  if [[ ! -f "${base}" ]]; then
    harness::report fail "policy-floor-present" \
      "no settings.base.json under the config root"
    return 1
  fi

  # One jq call for all three gates (mode "all"), rather than one per gate,
  # so a profile switch does not pay for three separate parses of the same
  # two files.
  result="$(jq -s --arg mode all -f "${gates}" -- "${base}" "${profile}")" || {
    harness::report fail "gates" "jq failed to evaluate the gates"
    return 1
  }

  local mode gate_ok message
  local failed=0
  while IFS=$'\t' read -r mode gate_ok message; do
    if [[ "${gate_ok}" == "true" ]]; then
      harness::report pass "${mode}" ""
    else
      failed=1
      harness::report fail "${mode}" "${message}"
    fi
  done < <(printf '%s' "${result}" | jq -r '
      .gates[] | [
        .predicate,
        (.ok | tostring),
        ([ .checks[] | select(.ok == false)
           | .name + "(" + ([ .violations[] | (.path // .bad_name // .found // "?") ] | join(",")) + ")" ]
         | join(" "))
      ] | @tsv')
  return "${failed}"
}

#######################################
# Check the apiKeyHelper contract without running the helper. Clauses 1
# through 5 of the contract in docs/design.md; clause 6, that the helper
# writes the credential to stdout, is stated and never verified.
# Arguments:
#   $1: the profile file.
# Outputs:
#   One report line per clause on STDOUT. Every path printed passes through
#   harness::tildify, so no account identifier reaches the output.
# Returns:
#   0 when every clause passes or the profile names no helper, 1 otherwise.
#######################################
harness::helper_contract() {
  local profile="$1"
  local base gates raw path mode repo_root plugin_root
  base="$(harness::base_file)"
  gates="$(harness::gates_filter)"

  raw="$(jq -r -s --arg mode helper-path -f "${gates}" -- "${base}" "${profile}" 2>/dev/null)"
  if [[ -z "${raw}" || "${raw}" == "null" ]]; then
    harness::report pass "helper-not-named" "this profile names no apiKeyHelper"
    return 0
  fi

  # A helper path is written for the harness, which expands a leading tilde.
  path="${raw/#\~/${HOME}}"

  local failed=0
  if [[ -e "${path}" ]]; then
    harness::report pass "helper-exists" "$(harness::tildify "${path}")"
  else
    harness::report fail "helper-exists" "$(harness::tildify "${path}")"
    return 1
  fi

  if [[ -f "${path}" ]]; then
    harness::report pass "helper-is-a-regular-file" ""
  else
    harness::report fail "helper-is-a-regular-file" "not a regular file"
    failed=1
  fi

  if [[ -x "${path}" ]]; then
    harness::report pass "helper-is-executable" ""
  else
    harness::report fail "helper-is-executable" "run chmod 700 on it"
    failed=1
  fi

  mode="$(harness::file_mode "${path}")" || mode="unknown"
  if [[ "${mode}" == *00 ]]; then
    harness::report pass "helper-is-private" "mode ${mode}"
  else
    harness::report fail "helper-is-private" \
      "mode ${mode}, so group or other can reach it; run chmod 700 on it"
    failed=1
  fi

  plugin_root="$(harness::plugin_root)"
  repo_root="$(git -C "${plugin_root}" rev-parse --show-toplevel 2>/dev/null)" || repo_root=""
  if [[ "${path}" == "${plugin_root}"/* ]] ||
    { [[ -n "${repo_root}" ]] && [[ "${path}" == "${repo_root}"/* ]]; }; then
    harness::report fail "helper-outside-the-repository" \
      "the helper sits inside a tracked tree, so it could be committed"
    failed=1
  else
    harness::report pass "helper-outside-the-repository" ""
  fi

  harness::report note "helper-not-executed" \
    "the contract's last clause, that it writes the credential to stdout, stays unverified by design"
  return "${failed}"
}

#######################################
# Run every gate and the helper contract against one profile.
# Arguments:
#   $1: the profile file.
# Returns:
#   0 when everything passes, 1 otherwise.
#######################################
harness::validate_profile() {
  local profile="$1"
  local failed=0
  harness::gates "${profile}" || failed=1
  harness::helper_contract "${profile}" || failed=1
  return "${failed}"
}
