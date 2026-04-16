#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/ubuntu}"
LOG_PATH="${LOG_PATH:-$REPO_DIR/outputs/qwenf1/train_logs/aws_phase12_docker_smoke.log}"
OUTPUT_DIR="${OUTPUT_DIR:-outputs/qwenf1/models/qwenf1_phase12_aws_docker_smoke}"

cd "$REPO_DIR"
mkdir -p outputs/qwenf1/train_logs outputs/qwenf1/models
rm -f outputs/training.lock

nohup docker compose --env-file .env.example -f docker-compose.unsloth.yml run --rm \
  -e UNSLOTH_MAX_STEPS=1 \
  -e UNSLOTH_NUM_EPOCHS=1 \
  -e UNSLOTH_OUTPUT_DIR="$OUTPUT_DIR" \
  -e UNSLOTH_SAVE_STEPS=0 \
  thor-train \
  bash scripts/train_qwenf1_phase12_strict_wsl.sh \
  > "$LOG_PATH" 2>&1 < /dev/null &

echo $! > "$REPO_DIR/outputs/qwenf1/train_logs/aws_phase12_docker_smoke.pid"
echo "started pid $(cat "$REPO_DIR/outputs/qwenf1/train_logs/aws_phase12_docker_smoke.pid")"
