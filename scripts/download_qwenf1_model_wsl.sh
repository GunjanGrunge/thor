#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:?Set HOST to the EC2 public DNS or IP}"
REMOTE_USER="${REMOTE_USER:-ubuntu}"
PEM_PATH="${PEM_PATH:-$HOME/.ssh/thor-train.pem}"

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
REMOTE_THOR_DIR="${REMOTE_THOR_DIR:-$WORKSPACE_ROOT/Thor}"
REMOTE_OUTPUT_DIR="${REMOTE_OUTPUT_DIR:-outputs/qwenf1/models/qwen3_4b_instruct2507_lora_v1}"

LOCAL_THOR_DIR="${LOCAL_THOR_DIR:-/mnt/c/Users/Bot/Desktop/Thor}"
LOCAL_MODELS_DIR="${LOCAL_MODELS_DIR:-$LOCAL_THOR_DIR/outputs/qwenf1/models}"
ARCHIVE_NAME="${ARCHIVE_NAME:-qwen3_4b_instruct2507_lora_v1.tar.gz}"

if [[ ! -f "$PEM_PATH" ]]; then
  echo "Missing PEM file: $PEM_PATH" >&2
  exit 1
fi

mkdir -p "$LOCAL_MODELS_DIR"

REMOTE_PARENT="$(dirname "$REMOTE_OUTPUT_DIR")"
REMOTE_NAME="$(basename "$REMOTE_OUTPUT_DIR")"

ssh -i "$PEM_PATH" -o StrictHostKeyChecking=accept-new "$REMOTE_USER@$HOST" \
  "set -euo pipefail; cd '$REMOTE_THOR_DIR'; test -d '$REMOTE_OUTPUT_DIR'; tar -czf '/tmp/$ARCHIVE_NAME' -C '$REMOTE_PARENT' '$REMOTE_NAME'"

scp -i "$PEM_PATH" "$REMOTE_USER@$HOST:/tmp/$ARCHIVE_NAME" "$LOCAL_MODELS_DIR/$ARCHIVE_NAME"

tar -xzf "$LOCAL_MODELS_DIR/$ARCHIVE_NAME" -C "$LOCAL_MODELS_DIR"

ssh -i "$PEM_PATH" -o StrictHostKeyChecking=accept-new "$REMOTE_USER@$HOST" \
  "rm -f '/tmp/$ARCHIVE_NAME'"

echo "Downloaded model to: $LOCAL_MODELS_DIR/$REMOTE_NAME"
