#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:?HOST is required}"
REMOTE_USER="${REMOTE_USER:-ubuntu}"
REMOTE_DIR="${REMOTE_DIR:-/home/ubuntu}"
REMOTE_SMOKE_PATH="${REMOTE_SMOKE_PATH:-/home/ubuntu/scripts/remote_thor_smoke_start.sh}"
KEY_DEST="${KEY_DEST:-$HOME/.ssh/thor-training-20260416-184056.pem}"

SCRIPT_ROOT="/mnt/c/Users/Bot/Desktop/Thor/scripts"

echo "[1/4] uploading Thor bundle to $REMOTE_USER@$HOST:$REMOTE_DIR"
HOST="$HOST" REMOTE_USER="$REMOTE_USER" REMOTE_DIR="$REMOTE_DIR" KEY_DEST="$KEY_DEST" \
  bash "$SCRIPT_ROOT/upload_thor_bundle_to_ec2_wsl.sh"

echo "[2/4] rebuilding and validating Docker image on remote host"
HOST="$HOST" REMOTE_USER="$REMOTE_USER" KEY_DEST="$KEY_DEST" \
  bash "$SCRIPT_ROOT/run_remote_thor_rebuild_validate_wsl.sh"

echo "[3/4] uploading remote smoke launcher"
HOST="$HOST" REMOTE_USER="$REMOTE_USER" REMOTE_PATH="$REMOTE_SMOKE_PATH" KEY_DEST="$KEY_DEST" \
  bash "$SCRIPT_ROOT/upload_remote_thor_smoke_script_wsl.sh"

echo "[4/4] starting remote smoke run"
HOST="$HOST" REMOTE_USER="$REMOTE_USER" KEY_DEST="$KEY_DEST" \
  bash "$SCRIPT_ROOT/thor_ec2_ssh_wsl.sh" bash "$REMOTE_SMOKE_PATH"

echo
echo "Smoke test launched. Monitor it with:"
echo "HOST=$HOST bash /mnt/c/Users/Bot/Desktop/Thor/scripts/thor_ec2_ssh_wsl.sh tail -f /home/ubuntu/outputs/qwenf1/train_logs/aws_phase12_docker_smoke.log"
