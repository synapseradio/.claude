#!/bin/bash
#
# Provision this checkout (`deps`) or install its tools (`tools`).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/repo-root.sh
source "${SCRIPT_DIR}/lib/repo-root.sh"
# shellcheck source=lib/stamp.sh
source "${SCRIPT_DIR}/lib/stamp.sh"
# shellcheck source=setup/deps.sh
source "${SCRIPT_DIR}/setup/deps.sh"
# shellcheck source=setup/tools.sh
source "${SCRIPT_DIR}/setup/tools.sh"
# shellcheck source=setup/run.sh
source "${SCRIPT_DIR}/setup/run.sh"

set -Eeuo pipefail

setup::run "$@"
