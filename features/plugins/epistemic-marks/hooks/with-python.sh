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

FAILURE_REASON=''

err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}

#######################################
# Print the path of the uv in the plugin data directory's bin.
# Globals:
#   CLAUDE_PLUGIN_DATA
# Outputs:
#   The path, on STDOUT.
# Returns:
#   0 where that uv is executable.
#######################################
resolve_plugin_uv() {
  [[ -x "${CLAUDE_PLUGIN_DATA}/bin/uv" ]] || return 1
  echo "${CLAUDE_PLUGIN_DATA}/bin/uv"
}

#######################################
# Download the installer script to a file, with curl or else wget.
# Globals:
#   FAILURE_REASON
#   UV_INSTALLER_URL
# Arguments:
#   The file to download into.
# Returns:
#   0 where the file holds the download; else 1, with FAILURE_REASON set.
#######################################
download_installer() {
  local file="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf -o "${file}" "${UV_INSTALLER_URL}" >&2
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "${file}" "${UV_INSTALLER_URL}" >&2
  else
    FAILURE_REASON='no curl or wget'
    return 1
  fi || {
    FAILURE_REASON='the installer download failed'
    return 1
  }
}

#######################################
# Install uv into the plugin data directory's bin with Astral's standalone
# installer, leaving shell profiles alone.
# Globals:
#   CLAUDE_PLUGIN_DATA
# Outputs:
#   Everything the download and the installer print, on STDERR.
#   FAILURE_REASON
# Returns:
#   0 where the installer ran to completion; else 1, with FAILURE_REASON set.
#######################################
install_uv() {
  local status=0
  local installer
  installer="$(mktemp "${TMPDIR:-/tmp}/uv-install.XXXXXX")" || {
    FAILURE_REASON='no temporary file could be made'
    return 1
  }

  # Standalone installer: https://docs.astral.sh/uv/getting-started/installation/
  # Environment variables: https://docs.astral.sh/uv/reference/installer/
  if download_installer "${installer}"; then
    UV_NO_MODIFY_PATH=1 UV_INSTALL_DIR="${CLAUDE_PLUGIN_DATA}/bin" \
      sh "${installer}" --quiet </dev/null >&2 || {
      status=1
      FAILURE_REASON='the installer failed'
    }
  else
    status=1
  fi

  rm -f -- "${installer}"
  return "${status}"
}

#######################################
# Print a JSON object holding the model-facing members and a systemMessage.
# Arguments:
#   The model-facing JSON members, without braces.
#   The system message text.
# Outputs:
#   One JSON object on STDOUT, systemMessage last.
#######################################
print_with_system_message() {
  printf '{%s,"systemMessage":"%s"}\n' "$1" "$2"
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
  local tail="this session runs with no epistemic-marks rule text and no checks. Where uv is missing, install it from ${UV_DOCS_URL}."
  local text="epistemic-marks: the hooks could not run under uv on Python 3.14 (${FAILURE_REASON}), so ${tail}"
  local unreadable_text="epistemic-marks: the hook event could not be read, so the hooks could not run under uv on Python 3.14 (${FAILURE_REASON}), and ${tail}"
  local fragment

  case "${event}" in
  SessionStart | SubagentStart | PostToolBatch)
    printf -v fragment '"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}' \
      "${event}" "${text}"
    print_with_system_message "${fragment}" "${text}"
    ;;
  PreToolUse)
    printf -v fragment '"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}' \
      "${text}"
    print_with_system_message "${fragment}" "${text}"
    ;;
  Stop | SubagentStop)
    if ! printf '%s' "${payload}" |
      grep -Eq '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
      printf -v fragment '"decision":"block","reason":"%s"' "${text}"
      print_with_system_message "${fragment}" "${text}"
    fi
    ;;
  *)
    printf -v fragment '"decision":"block","reason":"%s"' "${unreadable_text}"
    print_with_system_message "${fragment}" "${unreadable_text}"
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

  local uv=uv
  if ! command -v uv >/dev/null 2>&1; then
    uv="$(resolve_plugin_uv)" || {
      install_uv || true
      uv="$(resolve_plugin_uv)" || {
        [[ -n "${FAILURE_REASON}" ]] || FAILURE_REASON='it is still missing after the install'
        fail_launch
      }
    }
  fi

  export UV_PYTHON_INSTALL_DIR="${CLAUDE_PLUGIN_DATA}/python"
  export UV_CACHE_DIR="${CLAUDE_PLUGIN_DATA}/uv-cache"
  exec "${uv}" run --python 3.14 --no-project --quiet -- "$@"
}

main "$@"
