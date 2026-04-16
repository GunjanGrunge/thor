#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(dirname "$SCRIPT_ROOT")}"
THOR_DIR="${THOR_DIR:-$SCRIPT_ROOT}"
VENV_DIR="${VENV_DIR:-$THOR_DIR/.venv_train}"
LOCK_FILE="${LOCK_FILE:-$THOR_DIR/outputs/training.lock}"
RUNNING_IN_DOCKER="${THOR_CONTAINERIZED:-}"

if [[ -z "$RUNNING_IN_DOCKER" ]] && [[ -f "/.dockerenv" ]]; then
  RUNNING_IN_DOCKER="1"
fi

if [[ ! -d "$THOR_DIR" ]]; then
  echo "Missing Thor workspace: $THOR_DIR" >&2
  echo "Set THOR_DIR or create /workspace/Thor -> /mnt/c/Users/Bot/Desktop/Thor" >&2
  exit 1
fi

mkdir -p "$THOR_DIR/outputs"

if [[ -e "$LOCK_FILE" ]]; then
  EXISTING_PID="$(awk 'NR==1 {print $1}' "$LOCK_FILE" 2>/dev/null || true)"
  if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" >/dev/null 2>&1; then
    echo "Training lock exists: $LOCK_FILE" >&2
    echo "Another training job may be running with PID $EXISTING_PID." >&2
    exit 1
  fi

  echo "Removing stale training lock: $LOCK_FILE"
  rm -f "$LOCK_FILE"
fi

cleanup() {
  rm -f "$LOCK_FILE"
}
trap cleanup EXIT

echo "$$ $(date -Is)" > "$LOCK_FILE"

cd "$THOR_DIR"

if [[ -n "$RUNNING_IN_DOCKER" ]]; then
  echo "Containerized runtime detected; using the image Python environment."
elif [[ -x "$VENV_DIR/bin/activate" ]]; then
  source "$VENV_DIR/bin/activate"
elif [[ -d "$VENV_DIR" ]]; then
  echo "Training virtualenv directory exists but is not activatable at $VENV_DIR; using current Python environment."
else
  echo "Training virtualenv not found at $VENV_DIR; using current Python environment."
fi

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Neither python nor python3 is available in the active environment." >&2
  exit 1
fi

export PYTHONPATH="$THOR_DIR:${PYTHONPATH:-}"
export TORCHDYNAMO_DISABLE="${TORCHDYNAMO_DISABLE:-1}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True,max_split_size_mb:128}"
export UNSLOTH_BASE_MODEL="${UNSLOTH_BASE_MODEL:-unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit}"
export UNSLOTH_TRAIN_DATA="${UNSLOTH_TRAIN_DATA:-data/sft/final/qwenf1_train_v1.jsonl}"
export UNSLOTH_TRAIN_FORMAT="${UNSLOTH_TRAIN_FORMAT:-chat}"
export UNSLOTH_OUTPUT_DIR="${UNSLOTH_OUTPUT_DIR:-outputs/qwenf1/models/qwen35_4b_lora}"
export UNSLOTH_MAX_SEQ_LENGTH="${UNSLOTH_MAX_SEQ_LENGTH:-1024}"
export UNSLOTH_MAX_STEPS="${UNSLOTH_MAX_STEPS:-0}"
export UNSLOTH_NUM_EPOCHS="${UNSLOTH_NUM_EPOCHS:-2}"
export UNSLOTH_BATCH_SIZE="${UNSLOTH_BATCH_SIZE:-1}"
export UNSLOTH_GRAD_ACCUM="${UNSLOTH_GRAD_ACCUM:-16}"
export UNSLOTH_LEARNING_RATE="${UNSLOTH_LEARNING_RATE:-1e-5}"
export UNSLOTH_LR_SCHEDULER="${UNSLOTH_LR_SCHEDULER:-cosine}"
export UNSLOTH_MAX_GRAD_NORM="${UNSLOTH_MAX_GRAD_NORM:-1.0}"
export UNSLOTH_WEIGHT_DECAY="${UNSLOTH_WEIGHT_DECAY:-0.01}"
export UNSLOTH_SAVE_STEPS="${UNSLOTH_SAVE_STEPS:-0}"
export UNSLOTH_SAVE_TOTAL_LIMIT="${UNSLOTH_SAVE_TOTAL_LIMIT:-1}"
export UNSLOTH_LORA_R="${UNSLOTH_LORA_R:-16}"
export UNSLOTH_LORA_ALPHA="${UNSLOTH_LORA_ALPHA:-32}"
export UNSLOTH_LORA_DROPOUT="${UNSLOTH_LORA_DROPOUT:-0.0}"
export UNSLOTH_SEED="${UNSLOTH_SEED:-42}"

"$PYTHON_BIN" - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda:", torch.version.cuda)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device:", torch.cuda.get_device_name(0))
PY

"$PYTHON_BIN" scripts/train_qwenf1_unsloth.py
