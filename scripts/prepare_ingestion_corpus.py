from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonlines

from common import DATA_DIR, ensure_dir, stable_id


NORM_DIR = DATA_DIR / "normalized"
INGEST_DIR = DATA_DIR / "ingestion"


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("Âµg", "mcg")
    text = text.replace("â‰¥", ">=")
    text = text.replace("â‰¤", "<=")
    text = text.replace("â€™", "'")
    text = text.replace("â€œ", '"').replace("â€\u009d", '"')
    text = text.replace("â€“", "-").replace("â€”", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def dedupe_key(record: dict[str, Any]) -> str:
    source = record.get("source", "")
    title = clean_text(record.get("title", ""))
    summary = clean_text(record.get("summary", ""))
    return f"{source}|{title}|{summary[:400]}"


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text else []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c]


def build_text_blob(record: dict[str, Any]) -> str:
    parts = [
        f"Title: {clean_text(record.get('title', ''))}",
        f"Source: {record.get('source', '')}",
        f"Domain: {record.get('domain', '')}",
        f"Record Type: {record.get('record_type', '')}",
    ]
    summary = clean_text(record.get("summary", ""))
    if summary:
        parts.append(f"Summary: {summary}")
    content = record.get("content", {})
    if isinstance(content, dict):
        if "text" in content:
            parts.append(f"Text: {clean_text(str(content['text']))}")
        if "sections" in content and isinstance(content["sections"], dict):
            for key, value in content["sections"].items():
                parts.append(f"Section - {clean_text(str(key))}: {clean_text(str(value))}")
        if "abstract" in content and isinstance(content["abstract"], list):
            for item in content["abstract"]:
                label = clean_text(str(item.get("label") or "abstract"))
                text = clean_text(str(item.get("text") or ""))
                if text:
                    parts.append(f"{label}: {text}")
        if "nutrients" in content and isinstance(content["nutrients"], dict):
            nutrient_lines = []
            for name, meta in content["nutrients"].items():
                nutrient_lines.append(f"{name}: {meta.get('amount')} {meta.get('unit')}")
            if nutrient_lines:
                parts.append("Nutrients: " + "; ".join(nutrient_lines))
        if "ingredients" in content and isinstance(content["ingredients"], list):
            ingredient_lines = []
            for ing in content["ingredients"][:40]:
                ingredient_lines.append(clean_text(str(ing.get("name") or ing.get("ingredientGroup") or "")))
            if ingredient_lines:
                parts.append("Ingredients: " + "; ".join(i for i in ingredient_lines if i))
    return "\n".join(part for part in parts if part)


def main() -> None:
    ensure_dir(INGEST_DIR)
    source_path = NORM_DIR / "evidence_all.jsonl"
    cleaned_records: list[dict[str, Any]] = []
    seen: set[str] = set()

    with jsonlines.open(source_path, mode="r") as reader:
        for record in reader:
            key = dedupe_key(record)
            if key in seen:
                continue
            seen.add(key)
            cleaned = dict(record)
            cleaned["title"] = clean_text(str(cleaned.get("title", "")))
            cleaned["summary"] = clean_text(str(cleaned.get("summary", "")))
            cleaned_records.append(cleaned)

    cleaned_path = INGEST_DIR / "evidence_cleaned.jsonl"
    with jsonlines.open(cleaned_path, mode="w") as writer:
        writer.write_all(cleaned_records)

    chunks: list[dict[str, Any]] = []
    for record in cleaned_records:
        blob = build_text_blob(record)
        for index, chunk in enumerate(chunk_text(blob), start=1):
            chunks.append(
                {
                    "chunk_id": stable_id("chunk", f"{record['id']}:{index}:{chunk[:200]}"),
                    "record_id": record["id"],
                    "source": record.get("source"),
                    "domain": record.get("domain"),
                    "record_type": record.get("record_type"),
                    "title": record.get("title"),
                    "chunk_index": index,
                    "text": chunk,
                    "grounding_urls": record.get("grounding_urls", []),
                    "metadata": record.get("metadata", {}),
                }
            )

    chunks_path = INGEST_DIR / "evidence_chunks.jsonl"
    with jsonlines.open(chunks_path, mode="w") as writer:
        writer.write_all(chunks)

    manifest = {
        "cleaned_records": len(cleaned_records),
        "chunks": len(chunks),
        "source_path": str(source_path),
        "cleaned_path": str(cleaned_path),
        "chunks_path": str(chunks_path),
    }
    (INGEST_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
