#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:?HOST is required}"
REMOTE_DIR="${REMOTE_DIR:-/home/ubuntu}"
REMOTE_LOG="${REMOTE_LOG:-$REMOTE_DIR/outputs/qwenf1/train_logs/aws_phase12_docker_smoke.log}"

bash /mnt/c/Users/Bot/Desktop/Thor/scripts/thor_ec2_ssh_wsl.sh \
  bash -lc "cd '$REMOTE_DIR' && mkdir -p outputs/qwenf1/train_logs outputs/qwenf1/models && rm -f outputs/training.lock && nohup docker compose --env-file .env.example -f docker-compose.unsloth.yml run --rm -e UNSLOTH_MAX_STEPS=1 -e UNSLOTH_NUM_EPOCHS=1 -e UNSLOTH_OUTPUT_DIR=outputs/qwenf1/models/qwenf1_phase12_aws_docker_smoke -e UNSLOTH_SAVE_STEPS=0 thor-train bash scripts/train_qwenf1_phase12_strict_wsl.sh > '$REMOTE_LOG' 2>&1 < /dev/null &"
