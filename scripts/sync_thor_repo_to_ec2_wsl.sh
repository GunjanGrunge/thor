#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:?HOST is required}"
REMOTE_USER="${REMOTE_USER:-ubuntu}"
REMOTE_THOR_DIR="${REMOTE_THOR_DIR:-/home/ubuntu}"
KEY_SOURCE="${KEY_SOURCE:-/mnt/c/Users/Bot/Desktop/Thor/tmp/thor-training-20260416-184056.pem}"
KEY_DEST="${KEY_DEST:-$HOME/.ssh/thor-training-20260416-184056.pem}"
LOCAL_THOR_DIR="${LOCAL_THOR_DIR:-/mnt/c/Users/Bot/Desktop/Thor}"
CLEAN_REMOTE_CHECKPOINTS="${CLEAN_REMOTE_CHECKPOINTS:-1}"
CLEAN_REMOTE_LOCKS="${CLEAN_REMOTE_LOCKS:-1}"

if ! command -v rsync >/dev/null 2>&1; then
  echo "Missing required command: rsync" >&2
  exit 1
fi

mkdir -p "$(dirname "$KEY_DEST")"
cp "$KEY_SOURCE" "$KEY_DEST"
chmod 600 "$KEY_DEST"

SSH_RSH="ssh -o StrictHostKeyChecking=accept-new -i $KEY_DEST"

echo "[remote] ensuring target dir exists: $REMOTE_THOR_DIR"
ssh -o StrictHostKeyChecking=accept-new -i "$KEY_DEST" "$REMOTE_USER@$HOST" \
  "mkdir -p '$REMOTE_THOR_DIR'"

echo "[sync] rsync local Thor -> $REMOTE_USER@$HOST:$REMOTE_THOR_DIR"
rsync -az --delete \
  -e "$SSH_RSH" \
  --exclude ".git/" \
  --exclude ".venv*/" \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  --exclude "outputs/qwenf1/models/" \
  --exclude "outputs/tmp/" \
  "$LOCAL_THOR_DIR/" "$REMOTE_USER@$HOST:$REMOTE_THOR_DIR/"

if [[ "$CLEAN_REMOTE_LOCKS" == "1" || "$CLEAN_REMOTE_CHECKPOINTS" == "1" ]]; then
  echo "[remote] cleaning stale training state"
  ssh -o StrictHostKeyChecking=accept-new -i "$KEY_DEST" "$REMOTE_USER@$HOST" \
    bash -s -- "$REMOTE_THOR_DIR" "$CLEAN_REMOTE_LOCKS" "$CLEAN_REMOTE_CHECKPOINTS" <<'EOF'
set -euo pipefail
REMOTE_THOR_DIR="$1"
CLEAN_REMOTE_LOCKS="$2"
CLEAN_REMOTE_CHECKPOINTS="$3"

if [[ "$CLEAN_REMOTE_LOCKS" == "1" ]]; then
  find "$REMOTE_THOR_DIR/outputs" -type f -name training.lock -delete || true
fi

if [[ "$CLEAN_REMOTE_CHECKPOINTS" == "1" ]]; then
  find "$REMOTE_THOR_DIR/outputs" -type d -name "checkpoint-*" -prune -exec rm -rf {} + || true
fi
EOF
fi

echo "[done] remote repo refreshed on existing instance"
echo "[next] start training with:"
echo "HOST=$HOST bash /mnt/c/Users/Bot/Desktop/Thor/scripts/thor_ec2_ssh_wsl.sh bash /workspace/Thor/scripts/remote_phase12_start.sh"
