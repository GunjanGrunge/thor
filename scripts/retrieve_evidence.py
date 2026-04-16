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
EMBED_DIR = ROOT / "data" / "embeddings"


def sanitize_model_name(model_name: str) -> str:
    return model_name.replace("/", "__")


def maybe_set_windows_hf_cache() -> None:
    windows_cache = "/mnt/c/Users/Bot/.cache/huggingface"
    if Path(windows_cache).exists() and "HF_HOME" not in os.environ:
        os.environ["HF_HOME"] = windows_cache


def load_metadata(path: Path) -> list[dict[str, Any]]:
    with jsonlines.open(path, mode="r") as reader:
        return list(reader)


def retrieve_evidence(query: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", top_k: int = 8) -> list[dict[str, Any]]:
    maybe_set_windows_hf_cache()

    base_dir = EMBED_DIR / sanitize_model_name(model_name)
    metadata = load_metadata(base_dir / "metadata.jsonl")
    embeddings = np.load(base_dir / "embeddings.npy", mmap_mode="r")

    model = SentenceTransformer(model_name)
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)[0]

    scores = embeddings @ query_embedding
    top_indices = np.argsort(scores)[-top_k:][::-1]

    results = []
    for idx in top_indices.tolist():
        item = metadata[idx]
        results.append(
            {
                "score": float(scores[idx]),
                "chunk_id": item.get("chunk_id"),
                "record_id": item.get("record_id"),
                "source": item.get("source"),
                "domain": item.get("domain"),
                "record_type": item.get("record_type"),
                "title": item.get("title"),
                "text": item.get("text"),
                "grounding_urls": item.get("grounding_urls", []),
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--top-k", type=int, default=8)
    args = parser.parse_args()

    results = retrieve_evidence(args.query, model_name=args.model, top_k=args.top_k)

    print(json.dumps({"query": args.query, "results": results}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
