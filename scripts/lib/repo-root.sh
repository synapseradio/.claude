#!/bin/bash
#
# Locate this checkout, the primary checkout, and whether this checkout is a
# linked worktree. Call repo_root::init once from inside the checkout.

export REPO_ROOT='' PRIMARY_ROOT='' REPO_GIT_DIR='' REPO_GIT_COMMON_DIR=''

#######################################
# Set REPO_ROOT, PRIMARY_ROOT, REPO_GIT_DIR, and REPO_GIT_COMMON_DIR from the
# current directory. PRIMARY_ROOT is the parent of the common git directory.
# Globals:
#   REPO_ROOT, PRIMARY_ROOT, REPO_GIT_DIR, REPO_GIT_COMMON_DIR
# Arguments:
#   None
# Returns:
#   1 outside a git checkout.
#######################################
repo_root::init() {
  local out
  out="$(git rev-parse --path-format=absolute --show-toplevel --git-dir --git-common-dir)" ||
    return 1
  {
    read -r REPO_ROOT
    read -r REPO_GIT_DIR
    read -r REPO_GIT_COMMON_DIR
  } <<<"${out}"
  PRIMARY_ROOT="${REPO_GIT_COMMON_DIR%/*}"
}

repo_root::enter() {
  repo_root::init || return 1
  cd "${REPO_ROOT}" || return 1
}

#######################################
# Whether this checkout is a linked worktree: its git directory differs from
# the common git directory.
# Globals:
#   REPO_GIT_DIR, REPO_GIT_COMMON_DIR
# Arguments:
#   None
# Returns:
#   0 in a linked worktree, 1 in the primary checkout.
#######################################
repo_root::in_linked_worktree() {
  [[ "${REPO_GIT_DIR}" != "${REPO_GIT_COMMON_DIR}" ]]
}
