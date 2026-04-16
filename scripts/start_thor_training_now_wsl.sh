#!/usr/bin/env bash
set -euo pipefail

THOR_DIR="${THOR_DIR:-/mnt/c/Users/Bot/Desktop/Thor}"
PEM_SRC="${PEM_SRC:-/mnt/c/Users/Bot/Desktop/martha/tmp/martha-qwenft-20260414.pem}"
EC2_HOST="${EC2_HOST:?EC2_HOST is required}"
EC2_INSTANCE_ID="${EC2_INSTANCE_ID:?EC2_INSTANCE_ID is required}"

cd "$THOR_DIR"
mkdir -p outputs/qwenf1/train_logs ~/.ssh

cp "$PEM_SRC" ~/.ssh/thor-train.pem
chmod 600 ~/.ssh/thor-train.pem

read_env_val() {
  local key="$1"
  grep -E "^${key}=" .env | head -n1 | cut -d= -f2- | tr -d '\r'
}

export AWS_ACCESS_KEY_ID="$(read_env_val AWS_ACCESS_KEY_ID)"
export AWS_SECRET_ACCESS_KEY="$(read_env_val AWS_SECRET_ACCESS_KEY)"
export AWS_REGION="$(read_env_val AWS_REGION)"
export EC2_HOST
export EC2_KEY_PATH="$HOME/.ssh/thor-train.pem"
export EC2_INSTANCE_ID

RUN_ID="$(date +%Y%m%d_%H%M%S)"
LOG_PATH="outputs/qwenf1/train_logs/orchestrator_${RUN_ID}.log"

nohup bash scripts/ec2_train_download_terminate_wsl.sh > "$LOG_PATH" 2>&1 &
echo "PID:$!"
echo "LOG:$LOG_PATH"
