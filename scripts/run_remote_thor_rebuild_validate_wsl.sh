#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:?HOST is required}"
REMOTE_USER="${REMOTE_USER:-ubuntu}"
REMOTE_PATH="${REMOTE_PATH:-/home/ubuntu/scripts/remote_thor_rebuild_validate.sh}"
LOCAL_SCRIPT="/mnt/c/Users/Bot/Desktop/Thor/scripts/remote_thor_rebuild_validate.sh"
KEY_DEST="${KEY_DEST:-$HOME/.ssh/thor-training-20260416-184056.pem}"

mkdir -p /tmp/thor-upload
cp "$LOCAL_SCRIPT" /tmp/thor-upload/remote_thor_rebuild_validate.sh

bash /mnt/c/Users/Bot/Desktop/Thor/scripts/thor_ec2_ssh_wsl.sh mkdir -p "$(dirname "$REMOTE_PATH")"
scp -o StrictHostKeyChecking=accept-new -i "$KEY_DEST" \
  /tmp/thor-upload/remote_thor_rebuild_validate.sh "$REMOTE_USER@$HOST:$REMOTE_PATH"
bash /mnt/c/Users/Bot/Desktop/Thor/scripts/thor_ec2_ssh_wsl.sh chmod +x "$REMOTE_PATH"
bash /mnt/c/Users/Bot/Desktop/Thor/scripts/thor_ec2_ssh_wsl.sh bash "$REMOTE_PATH"
