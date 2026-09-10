#!/bin/bash
#
# Run one of this plugin's hook scripts under the first Python on the path
# that can serve it, passing stdin and stdout through untouched.
#
# The hook commands name this rather than an interpreter, because `python3`
# on one machine is 3.14 and on another is a system Python below 3.14, where
# the hook would exit before reading its payload and the session would start
# with no user rules and no verification, silently.
#
# The floor is 3.14, not merely "recent": epistemic_marks/ledger.py catches
# `except OSError, ValueError:` without parentheses, grammar PEP 758 adds in
# 3.14, so an older interpreter fails to import the package at all rather
# than running it in some degraded way.

set -uo pipefail

readonly REQUIREMENT='Python 3.14 or later'
readonly CANDIDATES=(python3.14 python3)
readonly VERSION_PROBE='import sys; sys.exit(sys.version_info < (3, 14))'

err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}

#######################################
# Whether one interpreter can run the hook scripts.
# Globals:
#   VERSION_PROBE
# Arguments:
#   The interpreter's name or path.
# Returns:
#   0 where it exists and reports 3.14 or later.
#######################################
usable() {
  local candidate="$1"
  command -v "${candidate}" >/dev/null 2>&1 || return 1
  "${candidate}" -c "${VERSION_PROBE}" >/dev/null 2>&1
}

#######################################
# Exec the first usable interpreter against the arguments given.
# Globals:
#   CANDIDATES
#   REQUIREMENT
#   EPISTEMIC_MARKS_PYTHON
# Arguments:
#   The hook script to run, then its own arguments.
# Outputs:
#   One line on STDERR naming the requirement where no interpreter serves.
#######################################
main() {
  local candidate
  for candidate in "${EPISTEMIC_MARKS_PYTHON:-}" "${CANDIDATES[@]}"; do
    if [[ -n "${candidate}" ]] && usable "${candidate}"; then
      exec "${candidate}" "$@"
    fi
  done
  err "no interpreter runs the epistemic-marks hooks: they need ${REQUIREMENT}." \
    "Name one in EPISTEMIC_MARKS_PYTHON."
  exit 1
}

main "$@"
