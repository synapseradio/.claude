# shellcheck shell=bash
#
# Activation: writing the paths a profile declares into settings.json.
#
# Source this file; never execute it. It expects lib/common.sh sourced first.
#
# The write is bounded. It sets the leaf paths the profile declares and leaves
# every other key in settings.json exactly as it was, so whatever /config
# wrote there survives a profile switch.

if [[ -n "${HARNESS_ACTIVATE_SOURCED:-}" ]]; then
  return 0
fi
HARNESS_ACTIVATE_SOURCED=1

#######################################
# Copy settings.json aside before a write.
# Arguments:
#   $1: the settings file.
# Outputs:
#   The backup path on STDOUT, home-relativized.
#######################################
harness::backup_settings() {
  local settings="$1"
  local dir stamp target
  dir="$(harness::data_dir)/backups"
  mkdir -p -- "${dir}" || return 1
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  target="${dir}/settings.json.pre-${stamp}"
  cp -- "${settings}" "${target}" || return 1
  harness::tildify "${target}"
}

#######################################
# Write one profile's declared paths into settings.json and update the
# pointer. Reads the overlay through jq and applies it with a reduce over
# setpath, so exactly the declared leaves change.
# Arguments:
#   $1: the profile file.
#   $2: the profile name.
# Outputs:
#   Progress lines on STDOUT. No settings value appears in them.
# Returns:
#   0 on success.
#######################################
harness::activate_profile() {
  local profile="$1"
  local name="$2"
  local base gates settings overlay tmp backup

  base="$(harness::base_file)"
  gates="$(harness::gates_filter)"
  settings="$(harness::settings_file)"

  overlay="$(jq -s --arg mode overlay -f "${gates}" -- "${base}" "${profile}")" || {
    harness::err "could not read the profile's declared settings"
    return 1
  }

  if [[ -f "${settings}" ]]; then
    backup="$(harness::backup_settings "${settings}")" || {
      harness::err "could not back up settings.json"
      return 1
    }
    harness::report pass "backed-up" "${backup}"
  else
    printf '{}\n' >"${settings}" || {
      harness::err "could not create settings.json"
      return 1
    }
    harness::report pass "created" "$(harness::tildify "${settings}")"
  fi

  tmp="${settings}.harness-tmp"
  jq -s '
    .[0] as $settings
    | .[1] as $overlay
    | reduce ($overlay | paths(scalars)) as $p
        ($settings; setpath($p; $overlay | getpath($p)))
  ' -- "${settings}" <(printf '%s' "${overlay}") >"${tmp}" || {
    rm -f -- "${tmp}"
    harness::err "the bounded write failed, so settings.json is untouched"
    return 1
  }

  jq -e . -- "${tmp}" >/dev/null || {
    rm -f -- "${tmp}"
    harness::err "the merged result is not valid JSON, so settings.json is untouched"
    return 1
  }

  # A move within one directory is atomic, so no reader meets a half-written
  # settings file.
  mv -- "${tmp}" "${settings}" || {
    rm -f -- "${tmp}"
    harness::err "could not move the merged result into place"
    return 1
  }

  printf '%s\n' "${name}" >"$(harness::active_file)" || {
    harness::err "settings.json was written but the active pointer was not"
    return 1
  }

  harness::report pass "wrote-declared-paths" \
    "$(printf '%s' "${overlay}" | jq -r '[paths(scalars) | join(".")] | join(" ")')"
  harness::report pass "active-profile" "${name}"
  return 0
}
