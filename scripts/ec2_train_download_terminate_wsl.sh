#!/usr/bin/env bash
set -euo pipefail

# Full EC2 cycle:
# 1) run training on EC2 with live logs in current terminal
# 2) download final adapter to local workspace
# 3) remove remote checkpoint-* folders (optional)
# 4) self-terminate EC2 instance (optional)

EC2_HOST="${EC2_HOST:-}"
EC2_USER="${EC2_USER:-ubuntu}"
EC2_KEY_PATH="${EC2_KEY_PATH:-}"
EC2_INSTANCE_ID="${EC2_INSTANCE_ID:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"

THOR_DIR="${THOR_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REMOTE_THOR_DIR="${REMOTE_THOR_DIR:-/home/ubuntu}"
REMOTE_VENV_DIR="${REMOTE_VENV_DIR:-$REMOTE_THOR_DIR/.venv_train}"
REMOTE_OUTPUT_DIR="${REMOTE_OUTPUT_DIR:-outputs/qwenf1/models/qwen3_4b_instruct2507_lora_v1}"
REMOTE_LOG_DIR="${REMOTE_LOG_DIR:-$REMOTE_THOR_DIR/outputs/qwenf1/train_logs}"
RUN_NAME="${RUN_NAME:-qwenf1_$(date +%Y%m%d_%H%M%S)}"
REMOTE_LOG_PATH="$REMOTE_LOG_DIR/${RUN_NAME}.log"

LOCAL_DOWNLOAD_ROOT="${LOCAL_DOWNLOAD_ROOT:-$THOR_DIR/outputs/qwenf1/models}"
LOCAL_DOWNLOAD_NAME="${LOCAL_DOWNLOAD_NAME:-$(basename "$REMOTE_OUTPUT_DIR")}"
LOCAL_DOWNLOAD_DIR="${LOCAL_DOWNLOAD_DIR:-$LOCAL_DOWNLOAD_ROOT/$LOCAL_DOWNLOAD_NAME}"
LOCAL_ARCHIVE_PATH="${LOCAL_ARCHIVE_PATH:-$LOCAL_DOWNLOAD_ROOT/${LOCAL_DOWNLOAD_NAME}_${RUN_NAME}.tar.gz}"

SYNC_TO_EC2="${SYNC_TO_EC2:-0}"
REMOTE_CLEAN_BEFORE="${REMOTE_CLEAN_BEFORE:-1}"
DELETE_REMOTE_CHECKPOINTS="${DELETE_REMOTE_CHECKPOINTS:-1}"
TERMINATE_ON_SUCCESS="${TERMINATE_ON_SUCCESS:-1}"
TERMINATE_ON_FAILURE="${TERMINATE_ON_FAILURE:-0}"

# Remote training overrides (applied even if remote repo has older defaults).
# Keep these aligned with the strict phased run so an L4 does not inherit older,
# more aggressive settings from the remote repo state.
UNSLOTH_MAX_SEQ_LENGTH="${UNSLOTH_MAX_SEQ_LENGTH:-1024}"
UNSLOTH_BATCH_SIZE="${UNSLOTH_BATCH_SIZE:-1}"
UNSLOTH_GRAD_ACCUM="${UNSLOTH_GRAD_ACCUM:-4}"
UNSLOTH_LORA_R="${UNSLOTH_LORA_R:-8}"
UNSLOTH_LORA_ALPHA="${UNSLOTH_LORA_ALPHA:-16}"
PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True,max_split_size_mb:128}"

if [[ -z "$EC2_HOST" || -z "$EC2_KEY_PATH" || -z "$EC2_INSTANCE_ID" ]]; then
  echo "Missing required environment." >&2
  echo "Set: EC2_HOST, EC2_KEY_PATH, EC2_INSTANCE_ID" >&2
  exit 1
fi

for cmd in ssh scp aws tar; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
done

if [[ ! -f "$EC2_KEY_PATH" ]]; then
  echo "SSH key not found: $EC2_KEY_PATH" >&2
  exit 1
fi

mkdir -p "$LOCAL_DOWNLOAD_ROOT"

SSH_OPTS=(
  -i "$EC2_KEY_PATH"
  -o StrictHostKeyChecking=accept-new
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=10
)

TARGET="${EC2_USER}@${EC2_HOST}"
REMOTE_OUTPUT_PARENT="$(dirname "$REMOTE_OUTPUT_DIR")"
REMOTE_OUTPUT_NAME="$(basename "$REMOTE_OUTPUT_DIR")"

if [[ "$SYNC_TO_EC2" == "1" ]]; then
  if ! command -v rsync >/dev/null 2>&1; then
    echo "SYNC_TO_EC2=1 requested but rsync is not installed locally." >&2
    exit 1
  fi
  echo "[sync] rsync local Thor -> $TARGET:$REMOTE_THOR_DIR"
  rsync -az --delete \
    --exclude ".git/" \
    --exclude ".venv*/" \
    --exclude "outputs/" \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    "$THOR_DIR/" "$TARGET:$REMOTE_THOR_DIR/"
fi

echo "[remote] validating workspace + env"
ssh "${SSH_OPTS[@]}" "$TARGET" bash -s -- "$REMOTE_THOR_DIR" "$REMOTE_VENV_DIR" "$REMOTE_LOG_DIR" <<'EOF'
set -euo pipefail
REMOTE_THOR_DIR="$1"
REMOTE_VENV_DIR="$2"
REMOTE_LOG_DIR="$3"
test -d "$REMOTE_THOR_DIR"
if [[ -x "$REMOTE_VENV_DIR/bin/activate" ]]; then
  echo "[remote] using venv: $REMOTE_VENV_DIR"
elif command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1; then
  echo "[remote] no activatable venv at $REMOTE_VENV_DIR; wrapper will use current Python environment"
else
  echo "[remote] missing both activatable venv and system Python" >&2
  exit 1
fi
mkdir -p "$REMOTE_LOG_DIR"
EOF

if [[ "$REMOTE_CLEAN_BEFORE" == "1" ]]; then
  echo "[remote] cleaning stale lock + checkpoints before train"
  ssh "${SSH_OPTS[@]}" "$TARGET" bash -s -- "$REMOTE_THOR_DIR" <<'EOF'
set -euo pipefail
REMOTE_THOR_DIR="$1"
find "$REMOTE_THOR_DIR/outputs" -type f -name training.lock -delete || true
find "$REMOTE_THOR_DIR/outputs" -type d -name "checkpoint-*" -prune -exec rm -rf {} + || true
EOF
fi

echo "[train] starting remote training with live logs"
echo "[train] log: $REMOTE_LOG_PATH"
TRAIN_OK=0
if ssh "${SSH_OPTS[@]}" "$TARGET" bash -s -- "$REMOTE_THOR_DIR" "$REMOTE_VENV_DIR" "$REMOTE_OUTPUT_PARENT" "$REMOTE_LOG_PATH" "$REMOTE_OUTPUT_DIR" "$UNSLOTH_MAX_SEQ_LENGTH" "$UNSLOTH_BATCH_SIZE" "$UNSLOTH_GRAD_ACCUM" "$PYTORCH_CUDA_ALLOC_CONF" "$UNSLOTH_LORA_R" "$UNSLOTH_LORA_ALPHA" <<'EOF'
set -euo pipefail
REMOTE_THOR_DIR="$1"
REMOTE_VENV_DIR="$2"
REMOTE_OUTPUT_PARENT="$3"
REMOTE_LOG_PATH="$4"
REMOTE_OUTPUT_DIR="$5"
UNSLOTH_MAX_SEQ_LENGTH="$6"
UNSLOTH_BATCH_SIZE="$7"
UNSLOTH_GRAD_ACCUM="$8"
PYTORCH_CUDA_ALLOC_CONF="$9"
UNSLOTH_LORA_R="${10}"
UNSLOTH_LORA_ALPHA="${11}"
cd "$REMOTE_THOR_DIR"
mkdir -p "$REMOTE_OUTPUT_PARENT"
export UNSLOTH_OUTPUT_DIR="$REMOTE_OUTPUT_DIR"
export UNSLOTH_MAX_SEQ_LENGTH
export UNSLOTH_BATCH_SIZE
export UNSLOTH_GRAD_ACCUM
export PYTORCH_CUDA_ALLOC_CONF
export UNSLOTH_LORA_R
export UNSLOTH_LORA_ALPHA
export UNSLOTH_TRAIN_DATA="${UNSLOTH_TRAIN_DATA:-data/sft/final/qwenf1_train_phase12_strict_gold.jsonl}"
export UNSLOTH_NUM_EPOCHS="${UNSLOTH_NUM_EPOCHS:-6}"
export UNSLOTH_SAVE_STEPS="${UNSLOTH_SAVE_STEPS:-0}"
bash scripts/train_qwenf1_wsl.sh 2>&1 | tee "$REMOTE_LOG_PATH"
EOF
then
  TRAIN_OK=1
fi

if [[ "$TRAIN_OK" != "1" ]]; then
  echo "[train] failed"
  if [[ "$TERMINATE_ON_FAILURE" == "1" ]]; then
    echo "[aws] terminating failed instance: $EC2_INSTANCE_ID"
    aws ec2 terminate-instances --instance-ids "$EC2_INSTANCE_ID" --region "$AWS_REGION" >/dev/null
  fi
  exit 1
fi

echo "[download] packaging adapter on EC2"
ssh "${SSH_OPTS[@]}" "$TARGET" bash -s -- "$REMOTE_THOR_DIR" "$REMOTE_OUTPUT_DIR" "$REMOTE_OUTPUT_PARENT" "$REMOTE_OUTPUT_NAME" "$LOCAL_DOWNLOAD_NAME" "$RUN_NAME" <<'EOF'
set -euo pipefail
REMOTE_THOR_DIR="$1"
REMOTE_OUTPUT_DIR="$2"
REMOTE_OUTPUT_PARENT="$3"
REMOTE_OUTPUT_NAME="$4"
LOCAL_DOWNLOAD_NAME="$5"
RUN_NAME="$6"
cd "$REMOTE_THOR_DIR"
test -d "$REMOTE_OUTPUT_DIR"
tar -czf "/tmp/${LOCAL_DOWNLOAD_NAME}_${RUN_NAME}.tar.gz" -C "$REMOTE_OUTPUT_PARENT" "$REMOTE_OUTPUT_NAME"
EOF

echo "[download] copying adapter archive to local"
scp "${SSH_OPTS[@]}" "$TARGET:/tmp/${LOCAL_DOWNLOAD_NAME}_${RUN_NAME}.tar.gz" "$LOCAL_ARCHIVE_PATH"

echo "[download] extracting adapter to $LOCAL_DOWNLOAD_DIR"
rm -rf "$LOCAL_DOWNLOAD_DIR"
mkdir -p "$LOCAL_DOWNLOAD_ROOT"
tar -xzf "$LOCAL_ARCHIVE_PATH" -C "$LOCAL_DOWNLOAD_ROOT"

echo "[remote] removing temporary archive"
ssh "${SSH_OPTS[@]}" "$TARGET" "rm -f /tmp/${LOCAL_DOWNLOAD_NAME}_${RUN_NAME}.tar.gz"

if [[ "$DELETE_REMOTE_CHECKPOINTS" == "1" ]]; then
  echo "[remote] deleting checkpoint-* folders"
  ssh "${SSH_OPTS[@]}" "$TARGET" bash -s -- "$REMOTE_THOR_DIR" <<'EOF'
set -euo pipefail
REMOTE_THOR_DIR="$1"
find "$REMOTE_THOR_DIR/outputs" -type d -name "checkpoint-*" -prune -exec rm -rf {} +
EOF
fi

if [[ "$TERMINATE_ON_SUCCESS" == "1" ]]; then
  echo "[aws] terminating instance: $EC2_INSTANCE_ID"
  aws ec2 terminate-instances --instance-ids "$EC2_INSTANCE_ID" --region "$AWS_REGION" >/dev/null
fi

echo "[done] adapter downloaded to: $LOCAL_DOWNLOAD_DIR"
if [[ "$TERMINATE_ON_SUCCESS" == "1" ]]; then
  echo "[done] instance terminated; keep local logs from your terminal output for this run."
else
  echo "[done] log remains on EC2: $REMOTE_LOG_PATH"
fi
