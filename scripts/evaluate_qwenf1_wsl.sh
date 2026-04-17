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

if [[ -n "${RUNNING_IN_DOCKER:-}" ]]; then
  echo "Containerized runtime detected; using the image Python environment."
elif [[ -x "$VENV_DIR/bin/activate" ]]; then
  source "$VENV_DIR/bin/activate"
elif [[ -d "$VENV_DIR" ]]; then
  echo "Virtualenv directory exists but is not activatable at $VENV_DIR; using current Python environment."
else
  echo "Virtualenv not found at $VENV_DIR; using current Python environment."
fi

export PYTHONPATH="$THOR_DIR:${PYTHONPATH:-}"
export QWENF1_EVAL_BASE_MODEL="${QWENF1_EVAL_BASE_MODEL:-unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit}"
export QWENF1_EVAL_ADAPTER="${QWENF1_EVAL_ADAPTER:-outputs/qwenf1/models/qwen3_4b_instruct2507_lora_v1}"
export QWENF1_EVAL_SET="${QWENF1_EVAL_SET:-data/eval/qwenf1_eval_v1.jsonl}"
export QWENF1_EVAL_OUT_DIR="${QWENF1_EVAL_OUT_DIR:-outputs/qwenf1/eval/qwen3_4b_instruct2507_lora_v1}"

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Neither python nor python3 found in PATH." >&2
  exit 1
fi

$PYTHON_BIN scripts/evaluate_qwenf1_adapter.py "$@"
