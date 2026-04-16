#!/usr/bin/env bash
set -euo pipefail

EC2_HOST="${EC2_HOST:-}"
EC2_USER="${EC2_USER:-ubuntu}"
EC2_KEY_PATH="${EC2_KEY_PATH:-}"
REMOTE_LOG_PATH="${REMOTE_LOG_PATH:-}"
FOLLOW="${FOLLOW:-1}"
LINES="${LINES:-120}"

if [[ -z "$EC2_HOST" || -z "$EC2_KEY_PATH" || -z "$REMOTE_LOG_PATH" ]]; then
  echo "Missing required environment." >&2
  echo "Set: EC2_HOST, EC2_KEY_PATH, REMOTE_LOG_PATH" >&2
  exit 1
fi

if [[ ! -f "$EC2_KEY_PATH" ]]; then
  echo "SSH key not found: $EC2_KEY_PATH" >&2
  exit 1
fi

SSH_OPTS=(
  -i "$EC2_KEY_PATH"
  -o StrictHostKeyChecking=accept-new
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=10
)

TARGET="${EC2_USER}@${EC2_HOST}"
if [[ "$FOLLOW" == "1" ]]; then
  ssh "${SSH_OPTS[@]}" "$TARGET" "tail -n +1 -f \"$REMOTE_LOG_PATH\""
else
  ssh "${SSH_OPTS[@]}" "$TARGET" "tail -n \"$LINES\" \"$REMOTE_LOG_PATH\""
fi
