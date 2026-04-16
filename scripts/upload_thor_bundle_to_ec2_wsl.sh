#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:?HOST is required}"
REMOTE_USER="${REMOTE_USER:-ubuntu}"
BUNDLE_PATH="${BUNDLE_PATH:-/mnt/c/Users/Bot/Desktop/Thor/outputs/tmp/thor_docker_bundle.tgz}"
REMOTE_BUNDLE_PATH="${REMOTE_BUNDLE_PATH:-/tmp/thor_docker_bundle.tgz}"
REMOTE_DIR="${REMOTE_DIR:-/home/ubuntu}"

cd /mnt/c/Users/Bot/Desktop/Thor
mkdir -p outputs/tmp

tar -czf "$BUNDLE_PATH" \
  .dockerignore \
  Dockerfile.unsloth \
  docker-compose.unsloth.yml \
  requirements-train.txt \
  .env.example \
  scripts \
  data/sft/final/qwenf1_train_phase12_strict_gold.jsonl

bash /mnt/c/Users/Bot/Desktop/Thor/scripts/thor_ec2_ssh_wsl.sh mkdir -p "$REMOTE_DIR"
scp -o StrictHostKeyChecking=accept-new -i "${KEY_DEST:-$HOME/.ssh/thor-training-20260416-184056.pem}" \
  "$BUNDLE_PATH" "$REMOTE_USER@$HOST:$REMOTE_BUNDLE_PATH"
bash /mnt/c/Users/Bot/Desktop/Thor/scripts/thor_ec2_ssh_wsl.sh \
  bash -lc "cd '$REMOTE_DIR' && tar -xzf '$REMOTE_BUNDLE_PATH'"
