#!/bin/bash
#
# Locate this checkout, the primary checkout, and whether this checkout is a
# linked worktree. Call repo_root::init once from inside the checkout.

# The scripts that source this file read these variables, which shellcheck
# cannot follow from here.
# shellcheck disable=SC2034
REPO_ROOT=''
PRIMARY_ROOT=''
REPO_GIT_DIR=''
REPO_GIT_COMMON_DIR=''

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
  REPO_ROOT="$(git rev-parse --show-toplevel)" || return 1
  REPO_GIT_DIR="$(git rev-parse --path-format=absolute --git-dir)" || return 1
  REPO_GIT_COMMON_DIR="$(git rev-parse --path-format=absolute --git-common-dir)" || return 1
  PRIMARY_ROOT="${REPO_GIT_COMMON_DIR%/*}"
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
