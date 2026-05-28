#!/bin/bash
#
# Master on-off switch for Arbiter.
#
# `off` writes a sentinel file and kills the running daemon, if any.
# `on`  removes the sentinel and spawns the daemon via arbiter-up.sh.
# `status` prints the current state (on|off) and whether the daemon is
# actually listening.
#
# The sentinel path lives in arbiter-config.sh as ARBITER_DISABLED_FILE.
# arbiter-up.sh and arbiter-hook.py both read it; this script is the
# canonical way to flip it.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=arbiter-config.sh
source "${SCRIPT_DIR}/arbiter-config.sh"

#######################################
# Print usage to stderr and exit non-zero.
# Globals:
#   None
# Arguments:
#   None
# Returns:
#   Exits 2.
#######################################
usage() {
  cat >&2 <<'EOF'
Usage: arbiter-toggle.sh <on|off|status>

  on      Remove the disable sentinel and spawn the daemon.
  off     Write the disable sentinel and kill the running daemon.
  status  Print whether Arbiter is enabled and whether the daemon
          is listening.
EOF
  exit 2
}

#######################################
# Check whether something is already listening on the Arbiter port.
# Mirrors port_in_use() in arbiter-up.sh; duplicated here to keep this
# script self-contained without cross-sourcing helper functions.
# Globals:
#   ARBITER_HOST
#   ARBITER_PORT
# Arguments:
#   None
# Returns:
#   0 if a listener accepts a TCP connect within 1s, non-zero otherwise.
#######################################
port_in_use() {
  timeout 1 bash -c ">/dev/tcp/${ARBITER_HOST}/${ARBITER_PORT}" >/dev/null 2>&1
}

#######################################
# Kill the daemon recorded in ARBITER_PID_FILE if its process is still
# alive. Sends SIGTERM and waits up to 5s for the process to exit;
# escalates to SIGKILL if it does not. Removes the pid file regardless
# so a stale one does not linger. Silent when nothing is running.
# Globals:
#   ARBITER_PID_FILE
# Arguments:
#   None
# Returns:
#   0 always.
#######################################
stop_daemon() {
  if [[ ! -f "${ARBITER_PID_FILE}" ]]; then
    return 0
  fi
  local pid
  pid="$(cat "${ARBITER_PID_FILE}")"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}" 2>/dev/null || true
    local i
    for ((i = 0; i < 50; i++)); do
      if ! kill -0 "${pid}" 2>/dev/null; then
        break
      fi
      sleep 0.1
    done
    if kill -0 "${pid}" 2>/dev/null; then
      kill -9 "${pid}" 2>/dev/null || true
    fi
  fi
  rm -f "${ARBITER_PID_FILE}"
}

#######################################
# Disable Arbiter: write the sentinel and stop the daemon.
# Globals:
#   ARBITER_DISABLED_FILE
# Arguments:
#   None
# Returns:
#   0.
#######################################
turn_off() {
  mkdir -p "$(dirname "${ARBITER_DISABLED_FILE}")"
  : >"${ARBITER_DISABLED_FILE}"
  stop_daemon
  echo "arbiter: off (sentinel ${ARBITER_DISABLED_FILE})"
}

#######################################
# Enable Arbiter: remove the sentinel and spawn the daemon. Delegates
# spawn to arbiter-up.sh so a single code path governs startup.
# Globals:
#   ARBITER_DISABLED_FILE
#   SCRIPT_DIR
# Arguments:
#   None
# Returns:
#   0 on success; propagates arbiter-up.sh exit code on failure.
#######################################
turn_on() {
  rm -f "${ARBITER_DISABLED_FILE}"
  "${SCRIPT_DIR}/arbiter-up.sh"
  echo "arbiter: on"
}

#######################################
# Print the current sentinel state and listener state.
# Globals:
#   ARBITER_DISABLED_FILE
#   ARBITER_HOST
#   ARBITER_PORT
# Arguments:
#   None
# Returns:
#   0.
#######################################
show_status() {
  local switch listener
  if [[ -e "${ARBITER_DISABLED_FILE}" ]]; then
    switch="off"
  else
    switch="on"
  fi
  if port_in_use; then
    listener="listening on ${ARBITER_HOST}:${ARBITER_PORT}"
  else
    listener="not listening"
  fi
  echo "arbiter: ${switch} (${listener})"
}

main() {
  if [[ $# -ne 1 ]]; then
    usage
  fi
  case "$1" in
  on) turn_on ;;
  off) turn_off ;;
  status) show_status ;;
  *) usage ;;
  esac
}

main "$@"
