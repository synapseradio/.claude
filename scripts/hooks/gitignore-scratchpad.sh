#!/bin/bash
#
# PostToolUse hook for the Write and Edit tools.
#
# Reads the hook input JSON from stdin and, when the written path sits under
# a scratchpad/ directory inside a git repository, adds `scratchpad/` to that
# repository's .gitignore unless the entry is already present.
#
# rules/scratchpad.md puts working notes at scratchpad/ in the repository root
# and requires the directory be gitignored before anything lands in it. Firing
# on the write rather than on session start means repositories where no scratch
# file is ever written stay untouched.
#
# Globals: none.
# Stdin:   PostToolUse hook JSON envelope.
# Stdout:  nothing.

set -euo pipefail

readonly ENTRY='scratchpad/'
readonly COMMENT='# Working notes, reviews, and throwaway scripts. Not part of the project.'

main() {
  local input file_path repo_root gitignore
  input="$(cat)"
  file_path="$(jq -r '.tool_input.file_path // ""' <<<"${input}")"

  if [[ "${file_path}" != */scratchpad/* ]]; then
    return 0
  fi

  if ! repo_root="$(git -C "$(dirname "${file_path}")" rev-parse --show-toplevel 2>/dev/null)"; then
    return 0
  fi

  gitignore="${repo_root}/.gitignore"

  if [[ -f "${gitignore}" ]] && grep -qxF "${ENTRY}" "${gitignore}"; then
    return 0
  fi

  if [[ -s "${gitignore}" ]]; then
    echo "" >>"${gitignore}"
  fi
  echo "${COMMENT}" >>"${gitignore}"
  echo "${ENTRY}" >>"${gitignore}"

  return 0
}

main "$@"
