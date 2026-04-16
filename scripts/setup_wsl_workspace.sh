#!/usr/bin/env bash
set -euo pipefail

THOR_SOURCE="${THOR_SOURCE:-/mnt/c/Users/Bot/Desktop/Thor}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"

if [[ ! -d "$THOR_SOURCE" ]]; then
  echo "Missing Thor source: $THOR_SOURCE" >&2
  exit 1
fi

if [[ ! -w "$(dirname "$WORKSPACE_ROOT")" ]]; then
  echo "Creating $WORKSPACE_ROOT requires sudo/root permissions." >&2
  echo "Run: sudo bash scripts/setup_wsl_workspace.sh" >&2
  exit 1
fi

mkdir -p "$WORKSPACE_ROOT"
ln -sfn "$THOR_SOURCE" "$WORKSPACE_ROOT/Thor"

echo "WSL workspace ready:"
ls -la "$WORKSPACE_ROOT"
