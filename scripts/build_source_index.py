from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import jsonlines

from common import DATA_DIR, ensure_dir, utc_now_iso


NORM_DIR = DATA_DIR / "normalized"
INGEST_DIR = DATA_DIR / "ingestion"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with jsonlines.open(path, mode="r") as reader:
        return list(reader)


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    metadata = record.get("metadata", {}) if isinstance(record.get("metadata"), dict) else {}
    content = record.get("content", {}) if isinstance(record.get("content"), dict) else {}
    urls = [url for url in record.get("grounding_urls", []) if isinstance(url, str) and url]
    return {
        "record_id": record.get("id"),
        "source": record.get("source"),
        "domain": record.get("domain"),
        "record_type": record.get("record_type"),
        "title": record.get("title"),
        "grounding_urls": urls,
        "tags": record.get("tags", []),
        "category": content.get("category") or metadata.get("category"),
        "provider": content.get("provider"),
        "metadata": metadata,
    }


def build_source_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_source[str(record.get("source", "unknown"))].append(record)

    sources: list[dict[str, Any]] = []
    for source, group in sorted(by_source.items()):
        domain_counts = Counter(str(item.get("domain", "unknown")) for item in group)
        record_type_counts = Counter(str(item.get("record_type", "unknown")) for item in group)
        provider_counts = Counter(str(item.get("provider", "unknown")) for item in group if item.get("provider"))
        category_counts = Counter(str(item.get("category", "unknown")) for item in group if item.get("category"))
        urls = sorted({url for item in group for url in item.get("grounding_urls", [])})
        sources.append(
            {
                "source": source,
                "records": len(group),
                "domains": dict(domain_counts),
                "record_types": dict(record_type_counts),
                "providers": dict(provider_counts),
                "categories": dict(category_counts),
                "url_count": len(urls),
                "sample_urls": urls[:10],
                "sample_titles": [str(item.get("title", "")) for item in group[:10]],
            }
        )

    return {
        "generated_at": utc_now_iso(),
        "normalized_path": str((NORM_DIR / "evidence_all.jsonl").resolve()),
        "record_index_path": str((INGEST_DIR / "source_records.jsonl").resolve()),
        "total_records": len(records),
        "distinct_sources": len(sources),
        "sources": sources,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(NORM_DIR / "evidence_all.jsonl"))
    parser.add_argument("--record-output", default=str(INGEST_DIR / "source_records.jsonl"))
    parser.add_argument("--summary-output", default=str(INGEST_DIR / "source_index.json"))
    args = parser.parse_args()

    input_path = Path(args.input)
    record_output = Path(args.record_output)
    summary_output = Path(args.summary_output)

    ensure_dir(record_output.parent)
    records = [compact_record(record) for record in load_jsonl(input_path)]

    with jsonlines.open(record_output, mode="w") as writer:
        writer.write_all(records)

    summary = build_source_summary(records)
    summary_output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
