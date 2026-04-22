#!/usr/bin/env bash
#
# check-doc-links.sh — idempotent wrapper around lychee for doc link checking.
#
# Usage: check-doc-links.sh [path]
#   path: directory or file to check. Default: current directory.
#
# Behaviour:
#   - If lychee is installed, runs it against the given path.
#   - If lychee is not installed, prints an install hint and exits 0 with a
#     non-fatal note. This keeps CI green until the tool is provisioned.
#   - Non-destructive. Does not write anywhere.
#   - Announces what it is about to do before doing it.
#
# Source (lychee): https://github.com/lycheeverse/lychee
# Shell style: https://google.github.io/styleguide/shellguide.html

set -euo pipefail

readonly DEFAULT_PATH="."
readonly INSTALL_HINT="Install with: 'brew install lychee' (macOS) or 'cargo install lychee'."

main() {
  local target_path="${1:-${DEFAULT_PATH}}"

  if [[ ! -e "${target_path}" ]]; then
    echo "ERROR: path not found: ${target_path}" >&2
    return 2
  fi

  echo "Checking doc links under: ${target_path}"

  if ! command -v lychee >/dev/null 2>&1; then
    echo "NOTE: lychee is not installed; skipping link check."
    echo "      ${INSTALL_HINT}"
    return 0
  fi

  echo "Running: lychee --no-progress ${target_path}"
  if lychee --no-progress "${target_path}"; then
    echo "Link check passed."
    return 0
  else
    echo "ERROR: lychee reported broken links in ${target_path}" >&2
    return 1
  fi
}

main "$@"
