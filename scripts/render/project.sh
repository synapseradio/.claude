#!/bin/bash
#
# Run the pi and opencode projections. Each writes under the home directory,
# so only the primary checkout may run them.

#######################################
# Run the three projection scripts, stopping at the first failure. Every
# argument reaches the two translators; own-opencode-key.py takes only
# --check.
# Arguments:
#   Projection flags: --check, --agent NAME.
# Outputs:
#   A refusal on STDERR, with exit status 2, in a linked worktree.
#######################################
render::project() {
  if repo_root::in_linked_worktree; then
    echo "project: projections run only from the primary checkout (${PRIMARY_ROOT}); this is a linked worktree" >&2
    exit 2
  fi
  local -a key_args=()
  local arg
  for arg in "$@"; do
    if [[ "${arg}" == --check ]]; then
      key_args=(--check)
    fi
  done
  local dir=scripts/agent-configs
  uv run --frozen python "${dir}/translate-for-pi.py" "$@" || return 1
  uv run --frozen python "${dir}/translate-for-opencode.py" "$@" || return 1
  uv run --frozen python "${dir}/own-opencode-key.py" ${key_args[@]+"${key_args[@]}"} || return 1
}
