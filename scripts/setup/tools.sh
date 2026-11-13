#!/bin/bash
#
# Install the tools the Brewfile lists, only where one is missing.

#######################################
# Install the Brewfile where `brew bundle check` finds a tool missing.
# Arguments:
#   None
#######################################
setup::tools() {
  brew bundle check --file Brewfile || brew bundle --file Brewfile || return 1
}
