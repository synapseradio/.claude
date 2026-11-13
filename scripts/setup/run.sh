#!/bin/bash
#
# The setup entry point's dispatcher: `deps` provisions this checkout and
# `tools` installs the Brewfile.

#######################################
# Dispatch one setup subcommand from the checkout's root.
# Arguments:
#   deps or tools.
# Outputs:
#   Usage on STDERR, with exit status 2, for any other subcommand.
#######################################
setup::run() {
  case "${1:-}" in
  deps | tools)
    repo_root::init || exit 1
    cd "${REPO_ROOT}" || exit 1
    "setup::$1" || exit 1
    ;;
  *)
    echo "usage: setup.sh deps|tools" >&2
    exit 2
    ;;
  esac
}
