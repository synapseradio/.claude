#!/bin/bash
#
# Verify the guards that keep this machine's material out of the repository.
#
# Each subcommand answers one question and prints its evidence, so a reviewer
# reads the output rather than trusting an exit status.
#
# Usage: harness-guard.sh <command> [directory]
#   ignore            every settings variant name is ignored by a rule
#   material [DIR]    no credential, private path, or account identifier in DIR
#   scripts           no shipped script reads settings values or runs a helper
#   all               the three above, in order
#
# The next line is a file-wide directive and must sit above the first
# command. It resolves the sourced library relative to this script.
# shellcheck source-path=SCRIPTDIR

set -o errexit
set -o nounset
set -o pipefail

readonly EXIT_USAGE=1
readonly EXIT_IGNORE=8
readonly EXIT_MATERIAL=9
readonly EXIT_SCRIPTS=10

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

# Names to test the ignore rules against. The last four name no file, which is
# the point: a rule that covers only what exists today covers nothing
# tomorrow.
readonly PROBE_NAMES=(
  settings.json
  settings.local.json
  settings.gemma.json
  settings.glm.json
  settings.zai.json
  settings.a-profile-nobody-has-added-yet.json
)

usage() {
  sed -n '5,12p' -- "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

#######################################
# Check that a rule ignores every probe name, and that no probe name is
# tracked. Two passes, because they catch different breaches: the rules pass
# proves the rules are right for a name no file uses, and the index pass
# proves nobody committed such a file already.
# Outputs:
#   git's own -v output per name, so the rule and its line number are visible.
# Returns:
#   0 when both passes hold.
#######################################
cmd_ignore() {
  local repo failed=0
  repo="$(git -C "$(harness::plugin_root)" rev-parse --show-toplevel)" || {
    harness::report fail "repository-found" "the plugin is not inside a git repository"
    return "${EXIT_IGNORE}"
  }

  # Probe each name at the repo root and again nested under the plugin's own
  # directory. An allowlist admits that directory (!features/** or the
  # like), and that entry is broad enough to admit a settings variant
  # dropped inside it, which is exactly the gap a rule landing only at the
  # root would miss.
  #
  # repo_rel comes from git itself (rev-parse --show-prefix), run from the
  # plugin root, rather than stripping the repo path as a string prefix off
  # the plugin root path: on macOS /tmp is a symlink to /private/tmp, so
  # `git -C ... rev-parse --show-toplevel` (symlink-resolved) and a
  # CLAUDE_PLUGIN_ROOT built from an unresolved $(pwd) or mktemp path
  # disagree on which one names the same directory, and the string strip
  # silently matches nothing.
  local plugin_root repo_rel name
  plugin_root="$(harness::plugin_root)"
  repo_rel="$(git -C "${plugin_root}" rev-parse --show-prefix)"
  repo_rel="${repo_rel%/}"
  local -a probes=("${PROBE_NAMES[@]}")
  if [[ -n "${repo_rel}" ]]; then
    for name in "${PROBE_NAMES[@]}"; do
      probes+=("${repo_rel}/${name}")
    done
  fi

  printf 'Rules pass: does a rule ignore each name, whether or not a file exists?\n'
  local rules_out
  rules_out="$(git -C "${repo}" check-ignore -v --non-matching --no-index "${probes[@]}" || true)"
  printf '%s\n' "${rules_out}"

  # Each line is "source:linenum:pattern<TAB>name", or "::<TAB>name" when no
  # rule matched at all. A matched pattern still fails the pass when it
  # starts with !: that is a later rule winning by re-admitting the name, so
  # the name is not actually ignored, which is the exact breach this pass
  # exists to catch.
  local unmatched=0 readmitted=0 meta pattern
  while IFS=$'\t' read -r meta _; do
    [[ -n "${meta}" ]] || continue
    if [[ "${meta}" == "::" ]]; then
      unmatched=1
      continue
    fi
    pattern="${meta#*:}"
    pattern="${pattern#*:}"
    [[ "${pattern}" == "!"* ]] && readmitted=1
  done <<<"${rules_out}"

  if ((unmatched)); then
    harness::report fail "every-variant-name-ignored" \
      "a name above matched no rule, shown by the leading ::"
    failed=1
  elif ((readmitted)); then
    harness::report fail "every-variant-name-ignored" \
      "a name above matched a rule beginning with !, which re-admits it rather than ignoring it"
    failed=1
  else
    harness::report pass "every-variant-name-ignored" "${#probes[@]} names"
  fi

  printf 'Index pass: is any settings variant already tracked?\n'
  local tracked
  tracked="$(git -C "${repo}" ls-files -- 'settings.json' 'settings.*.json' ':!settings.base.json' || true)"
  if [[ -n "${tracked}" ]]; then
    printf '%s\n' "${tracked}"
    harness::report fail "no-variant-tracked" "the files above are in the index"
    failed=1
  else
    harness::report pass "no-variant-tracked" "settings.base.json is the only tracked settings file"
  fi

  ((failed == 0)) || return "${EXIT_IGNORE}"
  return 0
}

# Files the scan skips, each with the reason a reviewer weighs. Four of them
# name the shapes the scan looks for, because they are the detectors, and one
# is somebody else's bytes kept verbatim. The list is printed on every run,
# so nothing goes unscanned quietly.
readonly EXCLUDED_FILES=(
  "profile-gates.jq:defines the credential shapes the gates reject"
  "predicates.jq:defines the same shapes for the alignment sweep"
  "harness-guard.sh:defines the shapes on this very list"
  "alignment-machine.md:documents the shapes as the sweep's secret guard"
  "settings-schema.json:vendored upstream bytes, checksummed, whose own examples name paths"
)

#######################################
# Scan a directory for material. Reports the file paths and never the matched
# text, so running the scan cannot itself leak what it found.
# Globals:
#   HOME, EXCLUDED_FILES
# Arguments:
#   $1: the directory, default the plugin root.
# Returns:
#   0 when nothing matched.
#######################################
cmd_material() {
  local dir="${1:-}"
  [[ -n "${dir}" ]] || dir="$(harness::plugin_root)"
  [[ -d "${dir}" ]] || harness::die "${EXIT_USAGE}" "no directory at ${dir}"

  # The account identifier is derived here and never written down, because
  # writing it down would put it in the repository this scan protects.
  local account
  account="$(basename -- "${HOME:-/nonexistent}")"

  # Each prefix requires the body a real credential carries, because a bare
  # prefix is not one. The value gate in scripts/lib/profile-gates.jq matches
  # the prefix alone, and it is right to: it reads one settings value, where a
  # leading sk- is already suspicious. This scan reads prose and code, where
  # sk- appears in a sentence describing it, so it takes the stricter form.
  local failed=0 entry
  local -a checks=(
    "credential-prefix:(sk-|ghp_|ghu_|gho_|ghs_|ghr_|xox[abprs]-|glpat-|npm_|hf_)[A-Za-z0-9_-]{16,}"
    "credential-prefix-cloud:(AKIA|ASIA)[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{20,}|ya29\.[A-Za-z0-9_-]{20,}"
    "bearer-token:Bearer [A-Za-z0-9_.=-]{16,}"
    "opaque-token:[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{8,}"
    "home-absolute-path:(/Users/|/home/)[A-Za-z0-9._-]+"
    "account-identifier:(/Users/|/home/)${account}([/[:space:]\"']|$)"
  )

  local -a excludes=()
  printf 'skipped, with the reason for each:\n'
  for entry in "${EXCLUDED_FILES[@]}"; do
    printf '  %-24s %s\n' "${entry%%:*}" "${entry#*:}"
    excludes+=("--exclude=${entry%%:*}")
  done

  # -l reports the file and never the line, so a match's text stays unread.
  harness::scan_checks "${dir}" -- --binary-files=without-match \
    --exclude-dir=.git --exclude-dir=node_modules "${excludes[@]}" \
    -- "${checks[@]}" || failed=1

  local helpers
  helpers="$(find "${dir}" -type f -name '*api*key*' -not -name '*.template.sh' || true)"
  if [[ -n "${helpers}" ]]; then
    printf '%s\n' "${helpers}"
    harness::report fail "no-api-key-helper-shipped" "the files above look like a helper"
    failed=1
  else
    harness::report pass "no-api-key-helper-shipped" "only the placeholder template"
  fi

  ((failed == 0)) || return "${EXIT_MATERIAL}"
  return 0
}

#######################################
# Reject constructs that would read a settings value or run a helper. This is
# the layer that catches a script somebody adds later.
# Returns:
#   0 when every shipped script is clean.
#######################################
cmd_scripts() {
  local root failed=0
  root="$(harness::plugin_root)"

  local -a checks=(
    "no-cat-of-a-settings-file:(cat|less|more|head|tail)[^|;&]*settings[^|;&]*\.json"
    "no-whole-file-jq:jq[[:space:]]+(-r[[:space:]]+)?'?\.'?[[:space:]]+[^|;&]*settings"
    "no-helper-execution:[\$]\([\$]?\{?(helper|api_key_helper|apiKeyHelper|HELPER)"
    "no-exported-credential:export[[:space:]]+[A-Z_]*(TOKEN|API_KEY|SECRET)="
  )

  # Scoped to the code this plugin actually ships and runs: scripts/ (every
  # executable and its lib/) and templates/ (the placeholder helper a user
  # copies). tests/ is deliberately out of scope: guards.bats and
  # activation.bats build these exact constructs as fixtures on purpose, to
  # prove this guard catches them, and skills/ is a separate skill's
  # human-run reference material, not a script this plugin executes.
  harness::scan_checks "${root}/scripts" "${root}/templates" \
    -- --include='*.sh' --include='*.bats' --include='*.jq' \
    -- "${checks[@]}" || failed=1

  # The template ships without the executable bit on purpose, so a copy
  # nobody edited cannot quietly half-work.
  local template="${root}/templates/api-key-helper.template.sh"
  if [[ -f "${template}" && -x "${template}" ]]; then
    harness::report fail "template-not-executable" "$(harness::tildify "${template}")"
    failed=1
  else
    harness::report pass "template-not-executable" ""
  fi

  ((failed == 0)) || return "${EXIT_SCRIPTS}"
  return 0
}

cmd_all() {
  local failed=0
  printf '== ignore\n'
  cmd_ignore || failed=1
  printf '== material\n'
  cmd_material || failed=1
  printf '== scripts\n'
  cmd_scripts || failed=1
  ((failed == 0)) || return 1
  printf 'every guard holds\n'
}

main() {
  harness::require_cmd git grep find
  case "${1:-}" in
  ignore) cmd_ignore ;;
  material) cmd_material "${2:-}" ;;
  scripts) cmd_scripts ;;
  all) cmd_all ;;
  -h | --help | help | '') usage ;;
  *)
    harness::err "unknown command '${1}'"
    usage >&2
    exit "${EXIT_USAGE}"
    ;;
  esac
}

main "$@"
