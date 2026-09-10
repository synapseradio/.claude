#!/bin/bash
#
# First-time setup on a machine with no secrets configured.
#
# It installs the guards, creates the directories a profile lives in, copies
# the helper template where a user can edit it, then verifies what it
# installed. Installing proves a line was written; verifying proves git and
# the harness agree. The two stay separate on purpose.
#
# It writes no credential, reads no credential, and runs no helper. It reads
# settings.base.json to merge permission rules into it, and reads no other
# settings file.
#
# Usage: harness-setup.sh [--dry-run]
#
# The next line is a file-wide directive and must sit above the first
# command. It resolves the sourced library relative to this script.
# shellcheck source-path=SCRIPTDIR

set -o errexit
set -o nounset
set -o pipefail

readonly EXIT_FAILED=12

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

DRY_RUN=0

# The ignore rules, verbatim. They land after every allowlist because a later
# rule wins, so they hold even where an allowlist admits the directory.
ignore_block() {
  cat <<'RULES'

# installed by harness-config: a settings variant carries one provider's
# endpoint, its model pins, and whichever credential source that provider
# authenticates with, so no variant enters git. These sit last because a
# later rule wins, so they hold against every allowlist above.
settings.json
settings.*.json
!settings.base.json
**/profiles/*.json
*api-key*.sh
*api_key*.sh
!*api-key*.template.sh
RULES
}

# The deny rules, as a settings fragment the merge folds into base. Reading a
# settings file into a model's context publishes whatever it holds, and a
# variant may hold a token at env.ANTHROPIC_AUTH_TOKEN. settings.base.json is
# absent from the list on purpose: it is the tracked floor, AuditBase
# precondition 3 requires it to name nothing exempt, and the skill cannot do
# its job without reading it.
deny_fragment() {
  cat <<'FRAGMENT'
[
  "Read(**/settings.json)",
  "Read(**/settings.*.json)",
  "Read(~/.claude/agents/**)",
  "Read(**/.claude/agents/**)",
  "Read(~/.claude/plugins/data/**)"
]
FRAGMENT
}

step() {
  printf '\n-- %s\n' "$*"
}

#######################################
# Create the data directories a profile and a backup live in.
#######################################
install_directories() {
  local data profiles
  data="$(harness::data_dir)"
  profiles="$(harness::profiles_dir)"
  if ((DRY_RUN == 1)); then
    harness::report note "would-create" "$(harness::tildify "${profiles}")"
    return 0
  fi
  mkdir -p -- "${profiles}" "${data}/backups"
  # BSD chmod reads -- as a filename rather than as end-of-options, so it is
  # omitted here and below. Every path reaching chmod is absolute.
  chmod 700 "${data}" "${profiles}" "${data}/backups"
  harness::report pass "data-directories" "$(harness::tildify "${data}")"
}

#######################################
# Append the ignore rules to the repository's .gitignore, once. Appending
# rather than rewriting keeps the existing allowlist intact.
#######################################
install_ignore_rules() {
  local repo target
  repo="$(git -C "$(harness::plugin_root)" rev-parse --show-toplevel)" || {
    harness::report fail "gitignore-found" "the plugin is not inside a git repository"
    return 1
  }
  target="${repo}/.gitignore"
  if [[ -f "${target}" ]] && grep -q 'installed by harness-config' -- "${target}"; then
    harness::report pass "ignore-rules" "already installed"
    return 0
  fi
  if [[ -f "${target}" ]] && grep -qx 'settings\.\*\.json' -- "${target}"; then
    harness::report pass "ignore-rules" "an equivalent rule is already present"
    return 0
  fi
  if ((DRY_RUN == 1)); then
    harness::report note "would-append" "$(harness::tildify "${target}")"
    ignore_block
    return 0
  fi
  ignore_block >>"${target}"
  harness::report pass "ignore-rules" "appended to $(harness::tildify "${target}")"
}

#######################################
# Merge the deny rules into settings.base.json, adding entries and removing
# none. It touches permissions.deny alone and no hook entry, because
# concurrent work owns the hooks in that file.
#######################################
install_deny_rules() {
  local base tmp added
  base="$(harness::base_file)"
  if [[ ! -f "${base}" ]]; then
    harness::report fail "deny-rules" \
      "no settings.base.json under $(harness::tildify "$(harness::config_dir)")"
    return 1
  fi

  added="$(jq -r --argjson want "$(deny_fragment)" '
    ([ $want[] | select(IN((.permissions.deny // [])[]) | not) ]) | length
  ' -- "${base}")"

  if [[ "${added}" == "0" ]]; then
    harness::report pass "deny-rules" "all five already present"
    return 0
  fi

  if ((DRY_RUN == 1)); then
    harness::report note "would-add" "${added} deny rule(s) to settings.base.json"
    return 0
  fi

  tmp="${base}.harness-tmp"
  jq --argjson want "$(deny_fragment)" '
    .permissions.deny = ((.permissions.deny // []) + $want | unique_by(.))
  ' -- "${base}" >"${tmp}"
  jq -e . -- "${tmp}" >/dev/null || {
    rm -f -- "${tmp}"
    harness::report fail "deny-rules" "the merge produced invalid JSON, base untouched"
    return 1
  }
  mv -- "${tmp}" "${base}"
  harness::report pass "deny-rules" "${added} added; run the alignment sweep to propagate"
}

#######################################
# Copy the helper template where a user edits it, without the executable bit
# so a copy nobody edited cannot quietly half-work.
#######################################
install_helper_template() {
  local template target
  template="$(harness::plugin_root)/templates/api-key-helper.template.sh"
  target="$(harness::data_dir)/api-key-helper.template.sh"
  if [[ ! -f "${template}" ]]; then
    harness::report fail "helper-template" "the template is missing from the plugin"
    return 1
  fi
  if ((DRY_RUN == 1)); then
    harness::report note "would-copy" "$(harness::tildify "${target}")"
    return 0
  fi
  cp -- "${template}" "${target}"
  chmod 600 "${target}"
  harness::report pass "helper-template" "$(harness::tildify "${target}")"
}

#######################################
# Print the five commands that carry a fresh machine to a working profile.
# Every path is home-relativized, so no account identifier appears.
#######################################
next_steps() {
  local scripts template
  scripts="$(harness::tildify "$(harness::plugin_root)/scripts")"
  template="$(harness::tildify "$(harness::data_dir)/api-key-helper.template.sh")"
  cat <<STEPS

Next, in order. Each step is a command to run, in this order.

  1. Put your credential in a file only you can read:
       mkdir -p "\${HOME}/.config/myprovider"
       printf 'MYPROVIDER_TOKEN=%s\\n' "\${MYPROVIDER_TOKEN}" \\
         > "\${HOME}/.config/myprovider/credential"
       chmod 600 "\${HOME}/.config/myprovider/credential"
     Set MYPROVIDER_TOKEN in your shell first, and do not paste the token
     into a command a transcript would keep.

  2. Install the helper and point it at that file:
       cp ${template} "\${HOME}/.config/myprovider/api-key.sh"
       chmod 700 "\${HOME}/.config/myprovider/api-key.sh"
     Edit the two readonly lines in its header, SECRET_FILE and
     SECRET_VARIABLE, to name the file and the variable from step 1.

  3. Create a profile, then edit the file it names:
       ${scripts}/harness-profile.sh add myprovider

  4. Check it. This never runs your helper:
       ${scripts}/harness-profile.sh validate myprovider

  5. Activate it, then start a new session:
       ${scripts}/harness-profile.sh use myprovider
STEPS
}

main() {
  harness::require_cmd jq git grep find

  if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
    printf 'dry run: nothing gets written\n'
  fi

  local failed=0

  step "installing"
  install_directories || failed=1
  install_ignore_rules || failed=1
  install_deny_rules || failed=1
  install_helper_template || failed=1

  if ((DRY_RUN == 1)); then
    printf '\ndry run complete\n'
    return 0
  fi

  step "verifying what was installed"
  bash "${SCRIPT_DIR}/harness-guard.sh" all || failed=1

  if ((failed != 0)); then
    printf '\nSetup left something unresolved. The failing lines above name it.\n'
    return "${EXIT_FAILED}"
  fi

  next_steps
}

main "$@"
