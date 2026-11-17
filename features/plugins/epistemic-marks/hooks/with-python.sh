#!/bin/bash
#
# Run one of this plugin's hook scripts under Python 3.14 through uv, passing
# stdin and stdout through untouched.
#
# The hook commands name this rather than an interpreter, because `python3`
# on one machine is a current release and on another is a system Python below
# the floor, where the hook would exit before reading its payload and the
# session would start with no user rules and no verification, silently.
#
# The floor is 3.14. uv provisions that interpreter where the system Python is
# older, and the hook scripts use only the standard library, so nothing is
# installed beside it. `--no-project` keeps the enclosing repository's
# pyproject from influencing which interpreter uv resolves. It never falls back
# to a system Python.
#
# Everything the launcher installs lands in the plugin's persistent data
# directory, ${CLAUDE_PLUGIN_DATA}, which survives plugin updates and which the
# harness exports to hooks; nothing is written under the home directory. The
# subdirectories bin, python and uv-cache sit beside the plugin's own
# verify-marks state. uv is resolved in this order: the uv on PATH, then
# ${CLAUDE_PLUGIN_DATA}/bin/uv, then an install of uv into that bin directory.
# A downloaded Python 3.14 and uv's cache go to python and uv-cache whichever uv
# runs. Where CLAUDE_PLUGIN_DATA is unset or empty, as outside the harness, the
# launcher fails before it resolves or installs anything. Data directory:
# https://code.claude.com/docs/en/hooks
#
# Where no uv can be had, a hook's stderr reaches the user alone, so the
# launcher reads the event from the payload and answers in the JSON that event
# shows the model, with exit 0, and also writes one line to stderr. An event it
# cannot read gets the one shape every event accepts without a hookEventName,
# the universal continue, stopReason and systemMessage fields, because
# hookSpecificOutput requires that name. Per-event output fields:
# https://code.claude.com/docs/en/hooks

set -uo pipefail

readonly REQUIREMENT='uv, to run the hooks under Python 3.14'
readonly UV_DOCS_URL='https://docs.astral.sh/uv/'
readonly UV_INSTALLER_URL='https://astral.sh/uv/install.sh'

INSTALLER_TMP=''
FAILURE_REASON=''

err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}

#######################################
# Print the path of the uv to run.
# Globals:
#   CLAUDE_PLUGIN_DATA
# Outputs:
#   The uv found on PATH, else the one in the plugin data directory's bin, on
#   STDOUT.
# Returns:
#   0 where a uv was found.
#######################################
resolve_uv() {
  command -v uv 2>/dev/null && return 0
  if [[ -x "${CLAUDE_PLUGIN_DATA}/bin/uv" ]]; then
    echo "${CLAUDE_PLUGIN_DATA}/bin/uv"
    return 0
  fi
  return 1
}

#######################################
# Download the installer script to a file, with curl or else wget.
# Globals:
#   INSTALLER_TMP
#   UV_INSTALLER_URL
# Returns:
#   0 where the file holds the download.
#######################################
download_installer() {
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf -o "${INSTALLER_TMP}" "${UV_INSTALLER_URL}" >&2
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "${INSTALLER_TMP}" "${UV_INSTALLER_URL}" >&2
  else
    return 1
  fi
}

#######################################
# Install uv into the plugin data directory's bin with Astral's standalone
# installer, leaving shell profiles alone.
# Globals:
#   CLAUDE_PLUGIN_DATA
#   INSTALLER_TMP
# Outputs:
#   Everything the download and the installer print, on STDERR.
#   FAILURE_REASON
# Returns:
#   0 where the installer ran to completion; else 1, with FAILURE_REASON set.
#######################################
install_uv() {
  local status=0
  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    FAILURE_REASON='no curl or wget'
    return 1
  fi
  INSTALLER_TMP="$(mktemp "${TMPDIR:-/tmp}/uv-install.XXXXXX")" || {
    FAILURE_REASON='no temporary file could be made'
    return 1
  }
  trap 'rm -f -- "${INSTALLER_TMP}"' EXIT

  # Standalone installer: https://docs.astral.sh/uv/getting-started/installation/
  # Environment variables: https://docs.astral.sh/uv/reference/installer/
  if download_installer; then
    UV_NO_MODIFY_PATH=1 UV_INSTALL_DIR="${CLAUDE_PLUGIN_DATA}/bin" \
      sh "${INSTALLER_TMP}" --quiet </dev/null >&2 || {
      status=1
      FAILURE_REASON='the installer failed'
    }
  else
    status=1
    FAILURE_REASON='the installer download failed'
  fi

  rm -f -- "${INSTALLER_TMP}"
  trap - EXIT
  return "${status}"
}

#######################################
# Answer a launcher failure in the JSON the payload's event shows the model.
# Globals:
#   FAILURE_REASON
#   UV_DOCS_URL
# Arguments:
#   The hook payload, as read from STDIN.
# Outputs:
#   One JSON object on STDOUT, or nothing for a Stop or SubagentStop payload
#   with stop_hook_active true, where a second block would loop. An event that
#   is unreadable or unknown gets a top-level block decision with the reason
#   and the system message.
#######################################
report_failure_to_model() {
  local payload="$1"
  local event
  event="$(printf '%s' "${payload}" |
    grep -o '"hook_event_name"[[:space:]]*:[[:space:]]*"[^"]*"' |
    head -n 1 | sed 's/.*:[[:space:]]*"\(.*\)"$/\1/')" || true
  local text="epistemic-marks: the hooks could not run under uv on Python 3.14 (${FAILURE_REASON}), so this session runs with no epistemic-marks rule text and no checks. Where uv is missing, install it from ${UV_DOCS_URL}."

  local unreadable_text="epistemic-marks: the hook event could not be read, so the hooks could not run under uv on Python 3.14 (${FAILURE_REASON}), and this session runs with no epistemic-marks rule text and no checks. Where uv is missing, install it from ${UV_DOCS_URL}."

  case "${event}" in
  SessionStart | SubagentStart | PostToolBatch)
    printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"},"systemMessage":"%s"}\n' \
      "${event}" "${text}" "${text}"
    ;;
  PreToolUse)
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"},"systemMessage":"%s"}\n' \
      "${text}" "${text}"
    ;;
  Stop | SubagentStop)
    if ! printf '%s' "${payload}" |
      grep -Eq '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
      printf '{"decision":"block","reason":"%s","systemMessage":"%s"}\n' \
        "${text}" "${text}"
    fi
    ;;
  *)
    printf '{"decision":"block","reason":"%s","systemMessage":"%s"}\n' \
      "${unreadable_text}" "${unreadable_text}"
    ;;
  esac
}

#######################################
# Report that the hooks cannot run, to the person on STDERR and to the model on
# STDOUT, then exit.
# Globals:
#   FAILURE_REASON
#   REQUIREMENT
#   UV_DOCS_URL
# Outputs:
#   One line on STDERR naming the requirement and the reason, and the
#   model-facing JSON on STDOUT.
# Returns:
#   Does not return: exits 0.
#######################################
fail_launch() {
  err "the epistemic-marks hooks need ${REQUIREMENT} (${FAILURE_REASON}); see ${UV_DOCS_URL}."
  report_failure_to_model "$(cat)"
  exit 0
}

#######################################
# Exec the hook script against Python 3.14 through uv, installing uv into the
# plugin data directory first where none is found.
# Globals:
#   CLAUDE_PLUGIN_DATA
#   FAILURE_REASON
#   UV_CACHE_DIR
#   UV_PYTHON_INSTALL_DIR
# Arguments:
#   The hook script to run, then its own arguments.
#######################################
main() {
  if [[ -z "${CLAUDE_PLUGIN_DATA:-}" ]]; then
    FAILURE_REASON='CLAUDE_PLUGIN_DATA is not set'
    fail_launch
  fi

  local uv
  if ! uv="$(resolve_uv)"; then
    install_uv || true
    uv="$(resolve_uv)" || {
      [[ -n "${FAILURE_REASON}" ]] || FAILURE_REASON='it is still missing after the install'
      fail_launch
    }
  fi

  export UV_PYTHON_INSTALL_DIR="${CLAUDE_PLUGIN_DATA}/python"
  export UV_CACHE_DIR="${CLAUDE_PLUGIN_DATA}/uv-cache"
  exec "${uv}" run --python 3.14 --no-project --quiet -- "$@"
}

main "$@"
