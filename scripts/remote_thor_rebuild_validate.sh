#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/ubuntu}"

cd "$REPO_DIR"

docker compose --env-file .env.example -f docker-compose.unsloth.yml build --no-cache thor-train

docker run --rm thor-unsloth:latest \
  bash -lc "set -euo pipefail; test -f /usr/include/python3.10/Python.h; python3 - <<'PY'
from pathlib import Path
print(Path('/usr/include/python3.10/Python.h').exists())
PY"
