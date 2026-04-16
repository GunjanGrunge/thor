#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THOR_DIR="${THOR_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"

cd "$THOR_DIR"
mkdir -p outputs/qwenf1/train_logs
rm -f outputs/training.lock
export UNSLOTH_TRAIN_DATA="${UNSLOTH_TRAIN_DATA:-data/sft/final/qwenf1_train_phase12_strict_gold.jsonl}"
export UNSLOTH_OUTPUT_DIR="${UNSLOTH_OUTPUT_DIR:-outputs/qwenf1/models/qwenf1_phase12_strict_lora}"
export UNSLOTH_MAX_SEQ_LENGTH="${UNSLOTH_MAX_SEQ_LENGTH:-1024}"
export UNSLOTH_NUM_EPOCHS="${UNSLOTH_NUM_EPOCHS:-6}"
export UNSLOTH_BATCH_SIZE="${UNSLOTH_BATCH_SIZE:-1}"
export UNSLOTH_GRAD_ACCUM="${UNSLOTH_GRAD_ACCUM:-4}"
export UNSLOTH_LEARNING_RATE="${UNSLOTH_LEARNING_RATE:-8e-6}"
export UNSLOTH_LR_SCHEDULER="${UNSLOTH_LR_SCHEDULER:-cosine}"
export UNSLOTH_WARMUP_STEPS="${UNSLOTH_WARMUP_STEPS:-10}"
export UNSLOTH_LORA_R="${UNSLOTH_LORA_R:-8}"
export UNSLOTH_LORA_ALPHA="${UNSLOTH_LORA_ALPHA:-16}"
export UNSLOTH_SAVE_STEPS="${UNSLOTH_SAVE_STEPS:-0}"
nohup bash scripts/train_qwenf1_wsl.sh > outputs/qwenf1/train_logs/phase12_strict_train.log 2>&1 < /dev/null &
echo "started"
