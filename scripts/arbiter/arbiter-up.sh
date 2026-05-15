#!/bin/bash
#
# Idempotent startup for the local mlx_lm.server backing Arbiter.
#
# If a process is already listening on ARBITER_PORT, exit 0 silently.
# Otherwise spawn mlx_lm.server in the background with the config
# from arbiter-config.sh. Writes pid to ARBITER_PID_FILE and
# stdout/stderr to ARBITER_LOG_FILE. Designed to be safe under
# parallel invocation: multiple Claude Code SessionStart hooks racing
# each other will all converge on a single running server.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=arbiter-config.sh
source "${SCRIPT_DIR}/arbiter-config.sh"

#######################################
# Check whether something is already listening on the Arbiter port.
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
# Spawn the mlx_lm.server backing Arbiter if not already running,
# then wait for the /health endpoint to respond.
# Globals:
#   ARBITER_BIN, ARBITER_HOST, ARBITER_LOG_FILE, ARBITER_MODEL,
#   ARBITER_PID_FILE, ARBITER_PORT
# Arguments:
#   None
# Returns:
#   0 once the server accepts requests; 1 if prerequisites are
#   missing or the server fails to come up within 30s.
#######################################
main() {
  mkdir -p "$(dirname "${ARBITER_LOG_FILE}")" "$(dirname "${ARBITER_PID_FILE}")"

  if port_in_use; then
    exit 0
  fi

  if [[ ! -x "${ARBITER_BIN}" ]]; then
    echo "arbiter-up: mlx_lm.server not found or not executable at ${ARBITER_BIN}" >&2
    echo "          install with: pip install --user mlx-lm" >&2
    exit 1
  fi

  # Spawn detached so the server outlives this script (and the
  # Claude Code session that triggered it). --temp 0.0 pins decoding
  # to greedy; the Qwen3 /no_think directive lives in the system
  # prompt (lib/client.py) since mlx_lm.server has no CLI reasoning
  # toggle.
  nohup "${ARBITER_BIN}" \
    --model "${ARBITER_MODEL}" \
    --host "${ARBITER_HOST}" \
    --port "${ARBITER_PORT}" \
    --temp 0.0 \
    >>"${ARBITER_LOG_FILE}" 2>&1 &

  echo $! >"${ARBITER_PID_FILE}"

  # Brief readiness wait so SessionStart returns only when the server
  # can actually take requests. Bounded: if it never comes up in 30s,
  # log and bail rather than blocking the session indefinitely.
  for ((i = 0; i < 30; i++)); do
    if curl -fsS --max-time 1 "http://${ARBITER_HOST}:${ARBITER_PORT}/health" >/dev/null 2>&1; then
      exit 0
    fi
    sleep 1
  done

  echo "arbiter-up: server did not become ready within 30s — see ${ARBITER_LOG_FILE}" >&2
  exit 1
}

main "$@"
