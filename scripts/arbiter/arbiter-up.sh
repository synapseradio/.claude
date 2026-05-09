#!/bin/bash
#
# Idempotent startup for the local llama-server backing Arbiter.
#
# If a process is already listening on ARBITER_PORT, exit 0 silently.
# Otherwise spawn llama-server in the background with the config from
# arbiter-config.sh. Writes pid to ARBITER_PID_FILE and stdout/stderr
# to ARBITER_LOG_FILE. Designed to be safe under parallel invocation:
# multiple Claude Code SessionStart hooks racing each other will all
# converge on a single running server.

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
# Spawn the llama-server backing Arbiter if not already running, then
# wait for the /health endpoint to respond.
# Globals:
#   ARBITER_CTX
#   ARBITER_EXTRA_FLAGS
#   ARBITER_HOST
#   ARBITER_LOG_FILE
#   ARBITER_MODEL_PATH
#   ARBITER_PARALLEL
#   ARBITER_PID_FILE
#   ARBITER_PORT
# Arguments:
#   None
# Returns:
#   0 once the server accepts requests; 1 if prerequisites are missing
#   or the server fails to come up within 30s.
#######################################
main() {
  mkdir -p "$(dirname "${ARBITER_LOG_FILE}")" "$(dirname "${ARBITER_PID_FILE}")"

  if port_in_use; then
    exit 0
  fi

  # Sanity: the model file must exist before we spawn — otherwise
  # llama-server fails late with an opaque error after binding the port.
  if [[ ! -f "${ARBITER_MODEL_PATH}" ]]; then
    echo "arbiter-up: model file missing: ${ARBITER_MODEL_PATH}" >&2
    exit 1
  fi

  if ! command -v llama-server >/dev/null 2>&1; then
    echo "arbiter-up: llama-server not found in PATH" >&2
    exit 1
  fi

  # Spawn detached so the server outlives this script (and the
  # Claude Code session that triggered it).
  nohup llama-server \
    -m "${ARBITER_MODEL_PATH}" \
    --host "${ARBITER_HOST}" \
    --port "${ARBITER_PORT}" \
    --ctx-size "${ARBITER_CTX}" \
    --parallel "${ARBITER_PARALLEL}" \
    --log-prefix \
    "${ARBITER_EXTRA_FLAGS[@]}" \
    >> "${ARBITER_LOG_FILE}" 2>&1 &

  echo $! > "${ARBITER_PID_FILE}"

  # Brief readiness wait so SessionStart returns only when the server
  # can actually take requests. Bounded: if it never comes up in 30s,
  # log and bail rather than blocking the session indefinitely.
  for (( i = 0; i < 30; i++ )); do
    if curl -fsS --max-time 1 "http://${ARBITER_HOST}:${ARBITER_PORT}/health" >/dev/null 2>&1; then
      exit 0
    fi
    sleep 1
  done

  echo "arbiter-up: server did not become ready within 30s — see ${ARBITER_LOG_FILE}" >&2
  exit 1
}

main "$@"
