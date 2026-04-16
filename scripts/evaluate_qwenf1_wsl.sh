#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
THOR_DIR="${THOR_DIR:-$WORKSPACE_ROOT/Thor}"
VENV_DIR="${VENV_DIR:-$THOR_DIR/.venv_train}"

if [[ ! -d "$THOR_DIR" ]]; then
  echo "Missing Thor workspace: $THOR_DIR" >&2
  exit 1
fi

cd "$THOR_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Missing training virtualenv: $VENV_DIR" >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"

export PYTHONPATH="$THOR_DIR:${PYTHONPATH:-}"
export QWENF1_EVAL_BASE_MODEL="${QWENF1_EVAL_BASE_MODEL:-unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit}"
export QWENF1_EVAL_ADAPTER="${QWENF1_EVAL_ADAPTER:-outputs/qwenf1/models/qwen3_4b_instruct2507_lora_v1}"
export QWENF1_EVAL_SET="${QWENF1_EVAL_SET:-data/eval/qwenf1_eval_v1.jsonl}"
export QWENF1_EVAL_OUT_DIR="${QWENF1_EVAL_OUT_DIR:-outputs/qwenf1/eval/qwen3_4b_instruct2507_lora_v1}"

python scripts/evaluate_qwenf1_adapter.py "$@"
