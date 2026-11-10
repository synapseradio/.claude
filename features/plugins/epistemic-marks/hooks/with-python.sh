#!/bin/bash
#
# Run one of this plugin's hook scripts under the first Python on the path
# that can serve it, passing stdin and stdout through untouched.
#
# The hook commands name this rather than an interpreter, because `python3`
# on one machine is a current release and on another is a system Python below
# the floor, where the hook would exit before reading its payload and the
# session would start with no user rules and no verification, silently.
#
# The floor is 3.9, the oldest interpreter the test suite runs green on. The
# syntax limit is 3.8: the walrus operator at epistemic_marks/scan.py:164. An
# older interpreter fails to import the package at all rather than running it
# in some degraded way.

set -uo pipefail

readonly REQUIREMENT='Python 3.9 or later'
readonly CANDIDATES=(python3 python3.15 python3.14 python3.13 python3.12 python3.11 python3.10 python3.9)
readonly VERSION_PROBE='import sys; sys.exit(sys.version_info < (3, 9))'

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
#   0 where it exists and reports 3.9 or later.
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
