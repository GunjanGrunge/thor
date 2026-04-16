# Docker Training

Use Docker for Thor training to avoid WSL/PowerShell/remote shell drift. The goal is:

- one pinned CUDA image
- one mounted repo
- one training command
- outputs written back into the repo

## Files

- `Dockerfile.unsloth`
- `docker-compose.unsloth.yml`
- `scripts/train_qwenf1_phase12_docker.sh`

## Local GPU smoke test

From the repo root:

```bash
docker compose --env-file .env.example -f docker-compose.unsloth.yml build
docker compose --env-file .env.example -f docker-compose.unsloth.yml run --rm thor-train nvidia-smi
docker compose --env-file .env.example -f docker-compose.unsloth.yml run --rm thor-train bash scripts/train_qwenf1_phase12_strict_wsl.sh
```

The container now ignores any mounted repo `.venv_train` and always uses the
Python environment baked into the Docker image. This avoids host/AMI drift where
an old virtualenv shadows the image dependencies.

## EC2 workflow

On the EC2 host:

1. Install Docker and NVIDIA Container Toolkit once.
2. Copy or clone the Thor repo onto the instance.
3. Run:

```bash
cd /path/to/Thor
docker compose --env-file .env.example -f docker-compose.unsloth.yml build
docker compose --env-file .env.example -f docker-compose.unsloth.yml run --rm thor-train bash scripts/train_qwenf1_phase12_strict_wsl.sh | tee outputs/qwenf1/train_logs/phase12_strict_train.log
```

For an NVIDIA L4, keep the conservative strict-run settings unless you have
already proven headroom with a smoke test:

```bash
UNSLOTH_MAX_SEQ_LENGTH=1024 \
UNSLOTH_BATCH_SIZE=1 \
UNSLOTH_GRAD_ACCUM=4 \
UNSLOTH_LORA_R=8 \
UNSLOTH_LORA_ALPHA=16 \
bash scripts/train_qwenf1_phase12_docker.sh
```

## Monitoring

If training is running in the foreground:

```bash
tail -f outputs/qwenf1/train_logs/phase12_strict_train.log
```

If you want detached mode, switch to `docker compose up` and then use:

```bash
docker logs -f thor-unsloth-train
```

## Why this is better

- same Python/CUDA stack locally and on EC2
- no WSL virtualenv drift
- no PowerShell quoting issues
- no remote shell differences between bash and zsh
- repo remains mounted, so adapters and logs land in local files

## Practical recommendation

Use Docker for training and evaluation on EC2. Keep WSL only as a thin SSH client if you need to start or watch the run from Windows.
