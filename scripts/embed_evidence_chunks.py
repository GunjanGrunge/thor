from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import jsonlines
import numpy as np

from embedding_backend import encode_texts, sanitize_model_name
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INGEST_DIR = DATA_DIR / "ingestion"
EMBED_DIR = DATA_DIR / "embeddings"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_chunks(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with jsonlines.open(path, mode="r") as reader:
        for record in reader:
            records.append(record)
            if limit is not None and len(records) >= limit:
                break
    return records
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(INGEST_DIR / "evidence_chunks.jsonl"))
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    input_path = Path(args.input)
    records = load_chunks(input_path, args.limit)
    texts = [record["text"] for record in records]

    all_embeddings = []
    for i in range(0, len(texts), args.batch_size):
        batch_texts = texts[i : i + args.batch_size]
        all_embeddings.append(encode_texts(batch_texts, args.model))
        if (i // args.batch_size) % 10 == 0:
            print(f"Processed {min(i + args.batch_size, len(texts))}/{len(texts)} chunks")

    embeddings = np.vstack(all_embeddings).astype(np.float32)

    out_dir = EMBED_DIR / sanitize_model_name(args.model)
    ensure_dir(out_dir)

    metadata_path = out_dir / "metadata.jsonl"
    embeddings_path = out_dir / "embeddings.npy"
    manifest_path = out_dir / "manifest.json"

    with jsonlines.open(metadata_path, mode="w") as writer:
        writer.write_all(records)

    np.save(embeddings_path, embeddings)

    manifest = {
        "model": args.model,
        "input_path": str(input_path),
        "metadata_path": str(metadata_path),
        "embeddings_path": str(embeddings_path),
        "records": len(records),
        "dimensions": int(embeddings.shape[1]) if len(records) else 0,
        "normalized": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
