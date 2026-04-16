# AWS Unsloth Training

This project now has the same style of narrow Unsloth training stack used in
`C:\Users\Bot\Desktop\martha`, adapted for `QwenF1`.

## Base Model

Default base model:

```text
Qwen/Qwen3.5-4B
```

As of April 15, 2026, Unsloth documents support for the `Qwen3.5` family including:

- `Qwen3.5-0.8B`
- `Qwen3.5-2B`
- `Qwen3.5-4B`
- `Qwen3.5-9B`
- `Qwen3.5-27B`
- `Qwen3.5-35B-A3B`

References:

- https://unsloth.ai/docs/models/qwen3.5/fine-tune
- https://unsloth.ai/docs/models/qwen3.5

## Recommended First Run

Use the balanced dataset first:

```text
data/sft/final/qwenf1_train_v1.jsonl
```

This is the safer first training run because it avoids letting nutrition food records drown out workout and science rows.

## Standard WSL Workspace

Use the WSL workspace path:

```text
/workspace/Thor
```

It should point to:

```text
/mnt/c/Users/Bot/Desktop/Thor
```

Set it up from WSL:

```bash
cd /mnt/c/Users/Bot/Desktop/Thor
sudo bash scripts/setup_wsl_workspace.sh
```

Verify:

```bash
ls -la /workspace
```

Expected:

```text
Thor -> /mnt/c/Users/Bot/Desktop/Thor
```

## Files

- trainer: [scripts/train_qwenf1_unsloth.py](../scripts/train_qwenf1_unsloth.py)
- wrapper: [scripts/train_qwenf1_wsl.sh](../scripts/train_qwenf1_wsl.sh)
- workspace setup: [scripts/setup_wsl_workspace.sh](../scripts/setup_wsl_workspace.sh)
- training deps: [requirements-train.txt](../requirements-train.txt)
- balanced dataset: [data/sft/final/qwenf1_train_v1.jsonl](../data/sft/final/qwenf1_train_v1.jsonl)
- full-coverage dataset: [data/sft/final/qwenf1_train_v1_fullcoverage.jsonl](../data/sft/final/qwenf1_train_v1_fullcoverage.jsonl)

## Create The Training Environment

From WSL on the EC2 box or other Linux GPU host:

```bash
cd /workspace/Thor

python3 -m venv .venv_train
source .venv_train/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
python -m pip install -r requirements-train.txt
```

Verify CUDA:

```bash
python - <<'PY'
import torch
print(torch.__version__)
print(torch.version.cuda)
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no gpu")
PY
```

Use native Linux paths such as `/workspace/Thor/...` while training. Avoid
training directly from `/mnt/c/...` to reduce cross-filesystem overhead.

## Default Hyperparameters

These defaults are intentionally conservative for a first serious domain run:

- `UNSLOTH_BASE_MODEL=Qwen/Qwen3.5-4B`
- `UNSLOTH_TRAIN_DATA=data/sft/final/qwenf1_train_v1.jsonl`
- `UNSLOTH_TRAIN_FORMAT=chat`
- `UNSLOTH_OUTPUT_DIR=outputs/qwenf1/models/qwen35_4b_lora`
- `UNSLOTH_MAX_SEQ_LENGTH=2048`
- `UNSLOTH_NUM_EPOCHS=2`
- `UNSLOTH_BATCH_SIZE=2`
- `UNSLOTH_GRAD_ACCUM=8`
- `UNSLOTH_LEARNING_RATE=1e-5`
- `UNSLOTH_LR_SCHEDULER=cosine`
- `UNSLOTH_MAX_GRAD_NORM=1.0`
- `UNSLOTH_WEIGHT_DECAY=0.01`
- `UNSLOTH_SAVE_STEPS=0` (default: no intermediate checkpoints)
- `UNSLOTH_SAVE_TOTAL_LIMIT=1`
- `UNSLOTH_LORA_R=16`
- `UNSLOTH_LORA_ALPHA=32`
- `UNSLOTH_LORA_DROPOUT=0.0`

## Why Qwen3.5-4B First

`Qwen3.5-4B` is the closest match to the original `QwenF1` target and is now supported by Unsloth.

It is the right first run because:

- better standalone capacity than 2B models
- smaller and cheaper than 9B/27B for initial AWS iteration
- enough headroom to learn the domain-specific reasoning and screening style in this dataset

If the first run is stable and quality is promising, the next upgrade path is:

- `Qwen/Qwen3.5-9B`

## AWS Notes

The Martha repo did not contain an EC2 launcher script. What it did contain was:

- a proven Unsloth trainer
- a WSL wrapper script
- environment-variable based configuration

This repo mirrors that pattern. You can launch EC2 however you already do in AWS, then run:

```bash
cd /workspace/Thor
UNSLOTH_TRAIN_DATA=data/sft/final/qwenf1_train_phase12_strict_gold.jsonl \
UNSLOTH_OUTPUT_DIR=outputs/qwenf1/models/qwenf1_phase12_strict_lora \
UNSLOTH_MAX_SEQ_LENGTH=1024 \
UNSLOTH_NUM_EPOCHS=6 \
UNSLOTH_BATCH_SIZE=1 \
UNSLOTH_GRAD_ACCUM=4 \
UNSLOTH_LEARNING_RATE=8e-6 \
UNSLOTH_LR_SCHEDULER=cosine \
UNSLOTH_WARMUP_STEPS=10 \
UNSLOTH_LORA_R=8 \
UNSLOTH_LORA_ALPHA=16 \
UNSLOTH_SAVE_STEPS=0 \
bash scripts/train_qwenf1_wsl.sh
```

inside your prepared Linux training environment.

Do not hard-source `.venv_train/bin/activate` in launcher scripts. The wrapper
already handles "use venv if activatable, otherwise use current Python" and is
the only path that should decide that.

## EC2 Full-Cycle Automation (Train -> Download -> Terminate)

For a single command from WSL that runs training, streams logs live, downloads the
adapter locally, cleans remote checkpoints, and terminates the instance:

```bash
cd /mnt/c/Users/Bot/Desktop/Thor

export EC2_HOST="<ec2-public-dns-or-ip>"
export EC2_KEY_PATH="/mnt/c/Users/Bot/Desktop/martha/tmp/<your-key>.pem"
export EC2_INSTANCE_ID="i-xxxxxxxxxxxxxxxxx"
export AWS_REGION="us-east-1"

bash scripts/ec2_train_download_terminate_wsl.sh
```

Key defaults:

- `TERMINATE_ON_SUCCESS=1`
- `DELETE_REMOTE_CHECKPOINTS=1`
- output downloaded to:
  - `outputs/qwenf1/models/qwen3_4b_instruct2507_lora_v1`

Optional switches:

```bash
# do not terminate after success
TERMINATE_ON_SUCCESS=0 bash scripts/ec2_train_download_terminate_wsl.sh

# sync local repo to EC2 before training
SYNC_TO_EC2=1 bash scripts/ec2_train_download_terminate_wsl.sh

# also terminate on failed training run
TERMINATE_ON_FAILURE=1 bash scripts/ec2_train_download_terminate_wsl.sh
```

## Watch Training Live From WSL

If you already have a remote log path and want a pure watcher terminal:

```bash
export EC2_HOST="<ec2-public-dns-or-ip>"
export EC2_KEY_PATH="/mnt/c/Users/Bot/Desktop/martha/tmp/<your-key>.pem"
export REMOTE_LOG_PATH="/workspace/Thor/outputs/qwenf1/train_logs/<run>.log"
bash scripts/ec2_watch_training_wsl.sh
```

## Cleanup Old LoRA + Checkpoints (Local + EC2)

Dry-run first (default is dry-run):

```bash
bash scripts/cleanup_training_artifacts_wsl.sh
```

Apply local cleanup:

```bash
DRY_RUN=0 \
LOCAL_DELETE_CHECKPOINTS=1 \
LOCAL_DELETE_OLD_ADAPTERS=1 \
KEEP_LOCAL_ADAPTER=qwen3_4b_instruct2507_lora_v1 \
bash scripts/cleanup_training_artifacts_wsl.sh
```

Apply remote cleanup:

```bash
DRY_RUN=0 \
REMOTE_ENABLED=1 \
EC2_HOST="<ec2-public-dns-or-ip>" \
EC2_KEY_PATH="/mnt/c/Users/Bot/Desktop/martha/tmp/<your-key>.pem" \
REMOTE_DELETE_CHECKPOINTS=1 \
REMOTE_DELETE_OLD_ADAPTERS=1 \
KEEP_REMOTE_ADAPTER=qwen3_4b_instruct2507_lora_v1 \
bash scripts/cleanup_training_artifacts_wsl.sh
```

If you want a different first run, override via env vars:

```bash
UNSLOTH_OUTPUT_DIR=outputs/qwenf1/models/qwen35_4b_lora_exp1 \
UNSLOTH_NUM_EPOCHS=3 \
UNSLOTH_MAX_SEQ_LENGTH=2048 \
bash scripts/train_qwenf1_wsl.sh
```

## Recommended Training Order

1. Train `Qwen/Qwen3.5-4B` on `data/sft/final/qwenf1_train_v1.jsonl`
2. Evaluate behavior, factuality, and safety on held-out prompts
3. If quality is promising, run a second experiment with:
   - more epochs, or
   - `data/sft/final/qwenf1_train_v1_fullcoverage.jsonl`, or
   - `Qwen/Qwen3.5-9B`

## Important

Do not train directly from the entire raw scraped corpus.

Use:

- the curated final SFT dataset
- optionally the full-coverage SFT variant for follow-up experiments

The raw evidence corpus still matters for retrieval and later updates, but the model should be trained on transformed SFT rows, not raw HTML or raw abstracts.
