#!/bin/bash
#
# The render entry point's dispatcher: `render`, `check`, and `project`.

#######################################
# Dispatch one render subcommand from the checkout's root.
# Arguments:
#   render, check, or project, then project's flags.
# Outputs:
#   Usage on STDERR, with exit status 2, for any other subcommand.
#######################################
render::run() {
  case "${1:-}" in
  render | check | project)
    local subcommand="$1"
    shift
    repo_root::enter || exit 1
    "render::${subcommand}" "$@" || exit 1
    ;;
  *)
    echo "usage: render.sh render|check|project [args]" >&2
    exit 2
    ;;
  esac
}
