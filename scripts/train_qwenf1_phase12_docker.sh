#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose --env-file .env.example -f docker-compose.unsloth.yml run --rm \
  -e UNSLOTH_MAX_SEQ_LENGTH="${UNSLOTH_MAX_SEQ_LENGTH:-1024}" \
  -e UNSLOTH_BATCH_SIZE="${UNSLOTH_BATCH_SIZE:-1}" \
  -e UNSLOTH_GRAD_ACCUM="${UNSLOTH_GRAD_ACCUM:-4}" \
  -e UNSLOTH_LORA_R="${UNSLOTH_LORA_R:-8}" \
  -e UNSLOTH_LORA_ALPHA="${UNSLOTH_LORA_ALPHA:-16}" \
  -e UNSLOTH_SAVE_STEPS="${UNSLOTH_SAVE_STEPS:-0}" \
  thor-train \
  bash scripts/train_qwenf1_phase12_strict_wsl.sh
