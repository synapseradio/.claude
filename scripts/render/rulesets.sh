#!/bin/bash
#
# Render the rulesets pool into rulesets/-render and check that the pool and
# its rendered copy agree.

#######################################
# Run the rulesets CLI through its launcher, from the checkout's root.
# Arguments:
#   The CLI's arguments.
#######################################
render::rulesets_cli() {
  bash features/plugins/rulesets/hooks/with-python.sh \
    features/plugins/rulesets/lib/rulesets/cli.py "$@"
}

#######################################
# Render the pool.
# Arguments:
#   None
#######################################
render::render() {
  render::rulesets_cli render --root rulesets || return 1
}

#######################################
# Check the pool, then check that the rendered copy on disk matches the pool.
# Arguments:
#   None
#######################################
render::check() {
  render::rulesets_cli check --root rulesets || return 1
  render::rulesets_cli render --check --root rulesets || return 1
}
