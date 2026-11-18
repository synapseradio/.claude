#!/bin/bash
#
# Prints "wt" when worktrunk is on PATH and "git" otherwise.

set -euo pipefail

if command -v wt >/dev/null 2>&1; then
  echo 'wt'
else
  echo 'git'
fi
