#!/usr/bin/env bash
set -euo pipefail

echo "[host] docker"
docker --version
docker compose version

echo "[host] nvidia-smi"
nvidia-smi

echo "[container] nvidia-smi"
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
