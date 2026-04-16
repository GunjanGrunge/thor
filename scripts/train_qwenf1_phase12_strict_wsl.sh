#!/usr/bin/env bash
set -euo pipefail

# Strict phased sanity-check run.
# This intentionally points at the small gold dataset so we can test behavior
# without spending on a larger noisy run.

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

echo "Running strict phased training with:"
echo "  UNSLOTH_TRAIN_DATA=$UNSLOTH_TRAIN_DATA"
echo "  UNSLOTH_OUTPUT_DIR=$UNSLOTH_OUTPUT_DIR"
echo "  UNSLOTH_NUM_EPOCHS=$UNSLOTH_NUM_EPOCHS"
echo "  UNSLOTH_BATCH_SIZE=$UNSLOTH_BATCH_SIZE"
echo "  UNSLOTH_GRAD_ACCUM=$UNSLOTH_GRAD_ACCUM"
echo "  UNSLOTH_LORA_R=$UNSLOTH_LORA_R"
echo "  UNSLOTH_LORA_ALPHA=$UNSLOTH_LORA_ALPHA"

bash scripts/train_qwenf1_wsl.sh
