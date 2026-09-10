#!/bin/bash
#
# Run one of this plugin's hook scripts under the first Python on the path
# that can serve it, passing stdin and stdout through untouched.
#
# The hook commands name this rather than an interpreter, because `python3`
# on one machine is 3.14 and on another is a system Python below 3.12, where
# the hook would exit before reading its payload and the session would start
# with no user rules.

set -uo pipefail

readonly REQUIREMENT='Python 3.12 or later with pyyaml'
readonly CANDIDATES=(python3.14 python3.13 python3.12 python3)
readonly VERSION_PROBE='import sys, yaml; sys.exit(sys.version_info < (3, 12))'

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
#   0 where it exists, imports yaml, and reports 3.12 or later.
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
#   RULESETS_PYTHON
# Arguments:
#   The hook script to run, then its own arguments.
# Outputs:
#   One line on STDERR naming the requirement where no interpreter serves.
#######################################
main() {
  local candidate
  for candidate in "${RULESETS_PYTHON:-}" "${CANDIDATES[@]}"; do
    if [[ -n "${candidate}" ]] && usable "${candidate}"; then
      exec "${candidate}" "$@"
    fi
  done
  err "no interpreter runs the model-scoped-rulesets hooks: they need ${REQUIREMENT}." \
    "Name one in RULESETS_PYTHON."
  exit 1
}

main "$@"
