from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import jsonlines

from common import DATA_DIR, utc_now_iso


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with jsonlines.open(path, mode="r") as reader:
        return sum(1 for _ in reader)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-data", default=str(DATA_DIR / "sft" / "final" / "qwenf1_train_current_ready.jsonl"))
    parser.add_argument("--train-manifest", default=str(DATA_DIR / "sft" / "final" / "qwenf1_train_current_ready_manifest.json"))
    parser.add_argument("--normalized-manifest", default=str(DATA_DIR / "normalized" / "evidence_manifest.jsonl"))
    parser.add_argument("--source-index", default=str(DATA_DIR / "ingestion" / "source_index.json"))
    parser.add_argument("--ingestion-manifest", default=str(DATA_DIR / "ingestion" / "manifest.json"))
    parser.add_argument("--embedding-manifest", default=str(DATA_DIR / "embeddings" / "sentence-transformers__all-MiniLM-L6-v2" / "manifest.json"))
    parser.add_argument("--output", default=str(DATA_DIR / "sft" / "final" / "qwenf1_training_rag_bundle_manifest.json"))
    args = parser.parse_args()

    train_data_path = Path(args.train_data)
    train_manifest_path = Path(args.train_manifest)
    normalized_manifest_path = Path(args.normalized_manifest)
    source_index_path = Path(args.source_index)
    ingestion_manifest_path = Path(args.ingestion_manifest)
    embedding_manifest_path = Path(args.embedding_manifest)
    output_path = Path(args.output)

    source_counts: dict[str, int] = {}
    if normalized_manifest_path.exists():
        with jsonlines.open(normalized_manifest_path, mode="r") as reader:
            for row in reader:
                source = str(row.get("source", "unknown"))
                source_counts[source] = int(row.get("count", 0))

    source_index = load_json(source_index_path)
    ingestion_manifest = load_json(ingestion_manifest_path)
    training_manifest = load_json(train_manifest_path)
    embedding_manifest = load_json(embedding_manifest_path)
    chunk_count = int(ingestion_manifest.get("chunks", 0))
    embedded_count = int(embedding_manifest.get("records", 0)) if embedding_manifest else 0
    embedding_status = "current" if embedding_manifest and chunk_count == embedded_count else "stale"

    bundle = {
        "generated_at": utc_now_iso(),
        "training": {
            "dataset_path": str(train_data_path.resolve()),
            "dataset_examples": count_jsonl(train_data_path),
            "manifest_path": str(train_manifest_path.resolve()),
            "manifest": training_manifest,
        },
        "rag": {
            "normalized_sources": source_counts,
            "source_index_path": str(source_index_path.resolve()),
            "source_index_summary": {
                "total_records": source_index.get("total_records", 0),
                "distinct_sources": source_index.get("distinct_sources", 0),
            },
            "ingestion_manifest_path": str(ingestion_manifest_path.resolve()),
            "ingestion_manifest": ingestion_manifest,
            "embedding_manifest_path": str(embedding_manifest_path.resolve()),
            "embedding_status": embedding_status,
            "embedding_manifest": embedding_manifest,
        },
        "notes": [
            "Training data stays separate from the RAG corpus.",
            "The source index is the durable ledger for extracted evidence provenance.",
            "If embeddings are stale or missing, regenerate them from data/ingestion/evidence_chunks.jsonl.",
        ],
    }
    output_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(json.dumps(bundle, indent=2))


if __name__ == "__main__":
    main()
