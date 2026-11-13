#!/bin/bash
#
# Render the rulesets pool (`render`), check it (`check`), or run the pi and
# opencode projections (`project`).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/repo-root.sh
source "${SCRIPT_DIR}/lib/repo-root.sh"
# shellcheck source=render/rulesets.sh
source "${SCRIPT_DIR}/render/rulesets.sh"
# shellcheck source=render/project.sh
source "${SCRIPT_DIR}/render/project.sh"
# shellcheck source=render/run.sh
source "${SCRIPT_DIR}/render/run.sh"

set -Eeuo pipefail

render::run "$@"
