#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:?HOST is required}"
REMOTE_USER="${REMOTE_USER:-ubuntu}"
KEY_SOURCE="${KEY_SOURCE:-/mnt/c/Users/Bot/Desktop/Thor/tmp/thor-training-20260416-184056.pem}"
KEY_DEST="${KEY_DEST:-$HOME/.ssh/thor-training-20260416-184056.pem}"

mkdir -p "$(dirname "$KEY_DEST")"
export KEY_SOURCE KEY_DEST

python3 - <<'PY'
from pathlib import Path
import os

src = Path(os.environ["KEY_SOURCE"])
dst = Path(os.environ["KEY_DEST"])
text = src.read_text().strip()
head = "-----BEGIN RSA PRIVATE KEY-----"
foot = "-----END RSA PRIVATE KEY-----"
if not (text.startswith(head) and text.endswith(foot)):
    raise SystemExit(f"unexpected key format in {src}")
body = text[len(head):-len(foot)].strip()
chunks = [body[i:i+64] for i in range(0, len(body), 64)]
dst.write_text(head + "\n" + "\n".join(chunks) + "\n" + foot + "\n")
PY

chmod 600 "$KEY_DEST"

exec ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 -i "$KEY_DEST" "$REMOTE_USER@$HOST" "$@"
