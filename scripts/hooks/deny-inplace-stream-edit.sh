#!/bin/bash
#
# Forwarder. The guard that denies an in-place stream edit now ships in the
# bash-guards plugin; this keeps the path the live settings file names
# executable until that file names the plugin instead.
# See lib/forward-guard.sh for what happens when the plugin is absent.

set -euo pipefail

# shellcheck source=lib/forward-guard.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/forward-guard.sh"

forward_guard "${BASH_SOURCE[0]}" "$@"
