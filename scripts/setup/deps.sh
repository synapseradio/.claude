#!/bin/bash
#
# Provision a checkout: bun install, uv sync, and the gauge types copy. Each
# step runs when the hash of its inputs differs from its stamp or its product
# is missing, and writes its stamp only after it succeeds.

readonly SETUP_GAUGE_TYPES_PATH='features/mods/context-gauge/.claude-plugin/types'

#######################################
# Run one step unless its stamp matches and its product exists.
# Globals:
#   REPO_ROOT
# Arguments:
#   The step name, its product path, the hash of its inputs, then the command.
# Outputs:
#   "skip <step> (inputs unchanged)" or "run <step>".
# Returns:
#   1 where the command fails; the stamp is then left as it was.
#######################################
setup::step() {
  local name="$1" product="$2" hash="$3"
  shift 3
  if [[ -e "${product}" ]] && stamp::matches "${name}" "${hash}"; then
    echo "skip ${name} (inputs unchanged)"
    return 0
  fi
  echo "run ${name}"
  "$@" || return 1
  stamp::write "${name}" "${hash}" || return 1
}

#######################################
# Replace this checkout's gauge types with the primary checkout's copy. The
# copy lands in a staging sibling first, so the types directory is absent only
# between two renames; the mod's tsconfig extends a file inside it, and an
# editor's TypeScript server drops the extended config while it is missing. A
# staging or aside directory left by an interrupted run is cleared first.
# Globals:
#   PRIMARY_ROOT, SETUP_GAUGE_TYPES_PATH
# Arguments:
#   None
#######################################
setup::copy_gauge_types() {
  local target="${SETUP_GAUGE_TYPES_PATH}"
  local staging="${target}.staging" aside="${target}.old"
  mkdir -p -- "${target%/*}" || return 1
  rm -rf -- "${staging}" "${aside}" || return 1
  cp -R -- "${PRIMARY_ROOT}/${target}" "${staging}" || return 1
  if [[ -e "${target}" ]]; then
    mv -- "${target}" "${aside}" || return 1
  fi
  mv -- "${staging}" "${target}" || return 1
  rm -rf -- "${aside}" || return 1
}

#######################################
# The gauge types step: a linked worktree copies the types the engine
# generated in the primary checkout, and the primary checkout keeps its own.
# Globals:
#   PRIMARY_ROOT, SETUP_GAUGE_TYPES_PATH
# Arguments:
#   None
#######################################
setup::gauge_types() {
  if ! repo_root::in_linked_worktree; then
    echo "skip gauge-types (primary checkout)"
    return 0
  fi
  local source="${PRIMARY_ROOT}/${SETUP_GAUGE_TYPES_PATH}"
  if [[ ! -d "${source}" ]]; then
    echo "skip gauge-types (no types in the primary checkout)"
    return 0
  fi
  local -a inputs=()
  local file
  while IFS= read -r file; do
    inputs+=("${file}")
  done < <(find "${source}" -type f | LC_ALL=C sort)
  local hash
  hash="$(stamp::hash ${inputs[@]+"${inputs[@]}"})" || return 1
  setup::step gauge-types "${SETUP_GAUGE_TYPES_PATH}" "${hash}" \
    setup::copy_gauge_types || return 1
}

#######################################
# Run every provisioning step, in order.
# Arguments:
#   None
#######################################
setup::deps() {
  local hash
  hash="$(stamp::hash bun.lock package.json)" || return 1
  setup::step bun node_modules/.bin/biome "${hash}" \
    bun install --frozen-lockfile || return 1
  hash="$(stamp::hash uv.lock pyproject.toml)" || return 1
  setup::step uv .venv/bin/python "${hash}" \
    uv sync --frozen || return 1
  setup::gauge_types || return 1
}
