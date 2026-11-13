# Verification, formatting, provisioning, and rendering for this repository; each recipe names one entry script.

set positional-arguments
set shell := ["bash", "-euo", "pipefail", "-c"]

# List every recipe
default:
    just --list

# Run the test suites a scope selects
test *args:
    uv run --frozen python scripts/verify/cli.py test "$@"

# Run the check-only linters a scope selects
lint *args:
    uv run --frozen python scripts/verify/cli.py lint "$@"

# Format files through treefmt; no scope formats the whole tree
fmt *args:
    uv run --frozen python scripts/verify/cli.py fmt "$@"

# Format, then lint and test in parallel, for one scope
verify *args:
    uv run --frozen python scripts/verify/cli.py verify "$@"

# Print the job manifest as JSON
suites:
    uv run --frozen python scripts/verify/cli.py list --json

# Provision this worktree: bun install, uv sync, gauge types
setup:
    bash scripts/setup.sh deps

# Install the Brewfile tools
tools:
    bash scripts/setup.sh tools

# Render the rulesets pool into rulesets/-render
render:
    bash scripts/render.sh render

# Check the rulesets pool and its rendered copy
render-check:
    bash scripts/render.sh check

# Run the pi and opencode projections; refused in a linked worktree
project *args:
    bash scripts/render.sh project "$@"
