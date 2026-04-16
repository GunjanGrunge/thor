#!/usr/bin/env bash
set -euo pipefail

# Safe cleanup utility for local + EC2 training artifacts.
# Default mode is dry-run.

THOR_DIR="${THOR_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LOCAL_OUTPUT_ROOT="${LOCAL_OUTPUT_ROOT:-$THOR_DIR/outputs/qwenf1/models}"
KEEP_LOCAL_ADAPTER="${KEEP_LOCAL_ADAPTER:-qwen3_4b_instruct2507_lora_v1}"

LOCAL_DELETE_CHECKPOINTS="${LOCAL_DELETE_CHECKPOINTS:-1}"
LOCAL_DELETE_OLD_ADAPTERS="${LOCAL_DELETE_OLD_ADAPTERS:-0}"

REMOTE_ENABLED="${REMOTE_ENABLED:-0}"
EC2_HOST="${EC2_HOST:-}"
EC2_USER="${EC2_USER:-ubuntu}"
EC2_KEY_PATH="${EC2_KEY_PATH:-}"
REMOTE_THOR_DIR="${REMOTE_THOR_DIR:-/workspace/Thor}"
KEEP_REMOTE_ADAPTER="${KEEP_REMOTE_ADAPTER:-$KEEP_LOCAL_ADAPTER}"
REMOTE_DELETE_CHECKPOINTS="${REMOTE_DELETE_CHECKPOINTS:-1}"
REMOTE_DELETE_OLD_ADAPTERS="${REMOTE_DELETE_OLD_ADAPTERS:-0}"

DRY_RUN="${DRY_RUN:-1}"

SSH_OPTS=(
  -o StrictHostKeyChecking=accept-new
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=10
)

if [[ -n "$EC2_KEY_PATH" ]]; then
  SSH_OPTS=(-i "$EC2_KEY_PATH" "${SSH_OPTS[@]}")
fi

echo "[mode] DRY_RUN=$DRY_RUN"
echo "[local] root=$LOCAL_OUTPUT_ROOT keep=$KEEP_LOCAL_ADAPTER"

if [[ -d "$LOCAL_OUTPUT_ROOT" ]]; then
  if [[ "$LOCAL_DELETE_CHECKPOINTS" == "1" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      find "$LOCAL_OUTPUT_ROOT" -type d -name "checkpoint-*" -print
    else
      find "$LOCAL_OUTPUT_ROOT" -type d -name "checkpoint-*" -prune -exec rm -rf {} +
    fi
  fi

  if [[ "$LOCAL_DELETE_OLD_ADAPTERS" == "1" ]]; then
    while IFS= read -r adapter_dir; do
      base="$(basename "$adapter_dir")"
      [[ "$base" == "$KEEP_LOCAL_ADAPTER" ]] && continue
      if [[ "$DRY_RUN" == "1" ]]; then
        echo "$adapter_dir"
      else
        rm -rf "$adapter_dir"
      fi
    done < <(find "$LOCAL_OUTPUT_ROOT" -mindepth 1 -maxdepth 1 -type d)
  fi
fi

if [[ "$REMOTE_ENABLED" == "1" ]]; then
  if [[ -z "$EC2_HOST" || -z "$EC2_KEY_PATH" ]]; then
    echo "REMOTE_ENABLED=1 requires EC2_HOST and EC2_KEY_PATH" >&2
    exit 1
  fi

  TARGET="${EC2_USER}@${EC2_HOST}"
  echo "[remote] host=$TARGET keep=$KEEP_REMOTE_ADAPTER"

  ssh "${SSH_OPTS[@]}" "$TARGET" bash -s -- \
    "$REMOTE_THOR_DIR" \
    "$KEEP_REMOTE_ADAPTER" \
    "$REMOTE_DELETE_CHECKPOINTS" \
    "$REMOTE_DELETE_OLD_ADAPTERS" \
    "$DRY_RUN" <<'EOF'
set -euo pipefail
REMOTE_THOR_DIR="$1"
KEEP_REMOTE_ADAPTER="$2"
REMOTE_DELETE_CHECKPOINTS="$3"
REMOTE_DELETE_OLD_ADAPTERS="$4"
DRY_RUN="$5"
REMOTE_OUTPUT_ROOT="$REMOTE_THOR_DIR/outputs/qwenf1/models"

if [[ ! -d "$REMOTE_OUTPUT_ROOT" ]]; then
  exit 0
fi

if [[ "$REMOTE_DELETE_CHECKPOINTS" == "1" ]]; then
  if [[ "$DRY_RUN" == "1" ]]; then
    find "$REMOTE_OUTPUT_ROOT" -type d -name "checkpoint-*" -print
  else
    find "$REMOTE_OUTPUT_ROOT" -type d -name "checkpoint-*" -prune -exec rm -rf {} +
  fi
fi

if [[ "$REMOTE_DELETE_OLD_ADAPTERS" == "1" ]]; then
  while IFS= read -r adapter_dir; do
    base="$(basename "$adapter_dir")"
    [[ "$base" == "$KEEP_REMOTE_ADAPTER" ]] && continue
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "$adapter_dir"
    else
      rm -rf "$adapter_dir"
    fi
  done < <(find "$REMOTE_OUTPUT_ROOT" -mindepth 1 -maxdepth 1 -type d)
fi
EOF
fi

echo "[done] cleanup finished"
