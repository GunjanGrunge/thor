#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:?HOST is required}"
REMOTE_USER="${REMOTE_USER:-ubuntu}"
KEY_SOURCE="${KEY_SOURCE:-/mnt/c/Users/Bot/Desktop/martha/tmp/martha-qwenft-20260414.pem}"
KEY_DEST="${KEY_DEST:-$HOME/.ssh/thor-train.pem}"

mkdir -p "$(dirname "$KEY_DEST")"
cp "$KEY_SOURCE" "$KEY_DEST"
chmod 600 "$KEY_DEST"

ssh -o StrictHostKeyChecking=accept-new -i "$KEY_DEST" "$REMOTE_USER@$HOST" \
  "bash -lc 'cd /home/ubuntu && mkdir -p outputs/qwenf1/train_logs && rm -f outputs/training.lock && export THOR_DIR=/home/ubuntu UNSLOTH_TRAIN_DATA=data/sft/final/qwenf1_train_phase12_strict_gold.jsonl UNSLOTH_OUTPUT_DIR=outputs/qwenf1/models/qwenf1_phase12_strict_lora UNSLOTH_MAX_SEQ_LENGTH=1024 UNSLOTH_NUM_EPOCHS=6 UNSLOTH_BATCH_SIZE=1 UNSLOTH_GRAD_ACCUM=4 UNSLOTH_LEARNING_RATE=8e-6 UNSLOTH_LR_SCHEDULER=cosine UNSLOTH_WARMUP_STEPS=10 UNSLOTH_LORA_R=8 UNSLOTH_LORA_ALPHA=16 UNSLOTH_SAVE_STEPS=0 && nohup bash scripts/train_qwenf1_wsl.sh > outputs/qwenf1/train_logs/phase12_strict_train.log 2>&1 < /dev/null &'"
