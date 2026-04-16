from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import jsonlines
import numpy as np
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INGEST_DIR = DATA_DIR / "ingestion"
EMBED_DIR = DATA_DIR / "embeddings"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_model_name(model_name: str) -> str:
    return model_name.replace("/", "__")


def maybe_set_windows_hf_cache() -> None:
    windows_cache = "/mnt/c/Users/Bot/.cache/huggingface"
    if Path(windows_cache).exists() and "HF_HOME" not in os.environ:
        os.environ["HF_HOME"] = windows_cache


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
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    maybe_set_windows_hf_cache()

    input_path = Path(args.input)
    records = load_chunks(input_path, args.limit)
    texts = [record["text"] for record in records]

    model = SentenceTransformer(args.model)
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)

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
