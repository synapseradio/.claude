#!/bin/bash
#
# Run one of this plugin's hook scripts under the first Python on the path
# that can serve it, passing stdin and stdout through untouched.
#
# The hook commands name this rather than an interpreter, because `python3`
# on one machine is 3.14 and on another is a system Python below 3.14, where
# the hook would exit before reading its payload and the session would start
# with no user rules.
#
# With `--announce` ahead of the script, a launcher that finds no interpreter
# also prints a JSON `systemMessage` on stdout, which the harness shows the
# person and never puts into the agent's context. The part-1 entry of a
# session start carries the flag, so the message appears once.

set -uo pipefail

readonly REQUIREMENT='Python 3.14 or later with pyyaml'
readonly CANDIDATES=(python3.14 python3.15 python3)
readonly VERSION_PROBE='import sys, yaml; sys.exit(sys.version_info < (3, 14))'

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
#   0 where it exists, imports yaml, and reports 3.14 or later.
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
#   Optionally --announce, then the hook script to run, then its own arguments.
# Outputs:
#   One line on STDERR naming the requirement where no interpreter serves, and
#   with --announce the same message as JSON on STDOUT.
# Returns:
#   0 where no interpreter serves, so the session starts without the rules.
#######################################
main() {
  local announce=no
  if [[ "${1:-}" == "--announce" ]]; then
    announce=yes
    shift
  fi
  local candidate
  for candidate in "${RULESETS_PYTHON:-}" "${CANDIDATES[@]}"; do
    if [[ -n "${candidate}" ]] && usable "${candidate}"; then
      exec "${candidate}" "$@"
    fi
  done
  local message="no interpreter runs the rulesets hooks: they need ${REQUIREMENT}."
  message+=" Name one in RULESETS_PYTHON."
  err "${message}"
  if [[ "${announce}" == "yes" ]]; then
    printf '{"systemMessage": "%s"}\n' "${message}"
  fi
  exit 0
}

main "$@"
