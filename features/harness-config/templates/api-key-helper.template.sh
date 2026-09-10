#!/bin/bash
#
# Template for an apiKeyHelper. Copy it outside this repository, edit it, then
# name the copy in a profile's settings.apiKeyHelper.
#
# The harness runs this script and reads one credential from its stdout. This
# plugin never runs it and never reads it, so the credential exists in exactly
# one place: the file this script reads.
#
# Install it like this, and adjust the two paths to your provider:
#
#   mkdir -p "${HOME}/.config/myprovider"
#   cp api-key-helper.template.sh "${HOME}/.config/myprovider/api-key.sh"
#   chmod 700 "${HOME}/.config/myprovider/api-key.sh"
#
# The contract this file must satisfy:
#
#   1. It exists.
#   2. It is a regular file.
#   3. Its owner may execute it.
#   4. Its mode ends in 00, so neither group nor other can reach it.
#   5. Its path resolves outside every git repository and outside the plugin.
#   6. It writes the credential to stdout and nothing else.
#
# The plugin checks clauses 1 through 5 with harness-profile.sh validate.
# It never checks clause 6, because checking it means running this script and
# capturing a credential. You learn clause 6 holds when a session
# authenticates.
#
# As shipped this template deliberately fails clause 6: it writes a
# placeholder and exits non-zero, and it arrives without the executable bit.
# Both are on purpose, so a copy nobody edited cannot quietly half-work.

set -o errexit
set -o nounset
set -o pipefail

# Point this at the file holding your credential. Keep that file outside every
# repository, and give it mode 600.
readonly SECRET_FILE="${HOME}/.config/REPLACE-WITH-YOUR-PROVIDER/credential"

# Name the variable your secret file defines.
readonly SECRET_VARIABLE='REPLACE_WITH_YOUR_VARIABLE_NAME'

main() {
  if [[ "${SECRET_FILE}" == *REPLACE-WITH-YOUR-PROVIDER* ]]; then
    echo "This helper is still the unedited template." >&2
    echo "Edit SECRET_FILE and SECRET_VARIABLE, then chmod 700 this file." >&2
    return 1
  fi

  if [[ ! -r "${SECRET_FILE}" ]]; then
    echo "The credential file named in SECRET_FILE is missing or unreadable." >&2
    return 1
  fi

  # Read the credential and write it to stdout, once, with no trailing prose.
  # Nothing else in this script may write to stdout, because the harness reads
  # every byte of stdout as the credential.
  set -o allexport
  # shellcheck source=/dev/null
  source "${SECRET_FILE}"
  set +o allexport

  if [[ -z "${!SECRET_VARIABLE:-}" ]]; then
    echo "${SECRET_FILE} defines no ${SECRET_VARIABLE}." >&2
    return 1
  fi

  printf '%s' "${!SECRET_VARIABLE}"
}

main "$@"
