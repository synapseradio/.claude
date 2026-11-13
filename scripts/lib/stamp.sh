#!/bin/bash
#
# Skip work whose inputs have not changed: hash a set of files, compare the
# hash with the stamp a previous success wrote, and write a new stamp.
# Stamps live under $REPO_ROOT/.cache/verify/, so REPO_ROOT must be set.

#######################################
# Print the sha256 of the named files' paths and contents.
# Arguments:
#   One or more files.
# Outputs:
#   The hex digest.
# Returns:
#   1 where a file is unreadable or none is named.
#######################################
stamp::hash() {
  if (($# == 0)); then
    echo "stamp::hash needs at least one file" >&2
    return 1
  fi
  local listing
  listing="$(shasum -a 256 -- "$@")" || return 1
  printf '%s\n' "${listing}" | shasum -a 256 | cut -d ' ' -f 1
}

#######################################
# Whether a stamp holds the given hash.
# Globals:
#   REPO_ROOT
# Arguments:
#   The stamp name, then the hash.
# Returns:
#   0 where the stamp exists and equals the hash.
#######################################
stamp::path() {
  printf '%s\n' "${REPO_ROOT}/.cache/verify/$1.sha256"
}

stamp::matches() {
  local file
  file="$(stamp::path "$1")"
  [[ -f "${file}" && "$(<"${file}")" == "$2" ]]
}

#######################################
# Write a stamp.
# Globals:
#   REPO_ROOT
# Arguments:
#   The stamp name, then the hash.
#######################################
stamp::write() {
  local file
  file="$(stamp::path "$1")"
  mkdir -p "${file%/*}" || return 1
  printf '%s\n' "$2" >"${file}"
}
