from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonlines

from common import ensure_dir


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[int]]:
    if not path.exists():
        return [], []
    rows: list[dict[str, Any]] = []
    invalid_lines: list[int] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            invalid_lines.append(line_number)
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            invalid_lines.append(line_number)
            continue
        if isinstance(row, dict):
            rows.append(row)
        else:
            invalid_lines.append(line_number)
    return rows, invalid_lines


def clean_text(value: str) -> str:
    replacements = {
        "\u00a0": " ",
        "\ufffd": "",
        "ï¿½": "",
        "–": "-",
        "—": "-",
        "’": "'",
        "“": '"',
        "”": '"',
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return " ".join(value.split()).strip()


def clean_row(row: dict[str, Any]) -> dict[str, Any]:
    cleaned = json.loads(json.dumps(row))
    for message in cleaned.get("messages", []):
        if isinstance(message.get("content"), str):
            message["content"] = clean_text(message["content"])
    metadata = cleaned.get("metadata", {})
    if isinstance(metadata, dict):
        for key, value in list(metadata.items()):
            if isinstance(value, str):
                metadata[key] = clean_text(value)
    return cleaned


def record_id_of(row: dict[str, Any]) -> str:
    metadata = row.get("metadata", {})
    if isinstance(metadata, dict):
        record_id = metadata.get("record_id")
        if isinstance(record_id, str):
            return record_id
    return ""


def domain_of(row: dict[str, Any]) -> str:
    metadata = row.get("metadata", {})
    if isinstance(metadata, dict):
        domain = metadata.get("domain")
        if isinstance(domain, str):
            return domain
    return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-input", default="data/sft/final/qwenf1_train_phase12_strict_gold.jsonl")
    parser.add_argument("--behavior-input", default="data/sft/final/qwenf1_train_v2_behavior.jsonl")
    parser.add_argument("--output", default="data/sft/final/qwenf1_train_current_ready.jsonl")
    parser.add_argument("--manifest", default="data/sft/final/qwenf1_train_current_ready_manifest.json")
    args = parser.parse_args()

    strict_source_rows, strict_invalid_lines = load_jsonl(Path(args.strict_input))
    behavior_source_rows, behavior_invalid_lines = load_jsonl(Path(args.behavior_input))

    strict_rows = [clean_row(row) for row in strict_source_rows]
    behavior_rows = [clean_row(row) for row in behavior_source_rows]

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    strict_count = 0
    behavior_unique_count = 0

    for row in strict_rows:
        rid = record_id_of(row)
        if rid:
            seen.add(rid)
        merged.append(row)
        strict_count += 1

    for row in behavior_rows:
        rid = record_id_of(row)
        if rid and rid in seen:
            continue
        if rid:
            seen.add(rid)
        merged.append(row)
        behavior_unique_count += 1

    output_path = Path(args.output)
    ensure_dir(output_path.parent)
    with jsonlines.open(output_path, mode="w") as writer:
        writer.write_all(merged)

    domain_counts: Counter[str] = Counter()
    for row in merged:
        domain_counts[domain_of(row)] += 1

    manifest = {
        "strict_input": args.strict_input,
        "behavior_input": args.behavior_input,
        "output": args.output,
        "strict_examples_kept": strict_count,
        "behavior_unique_examples_added": behavior_unique_count,
        "total_examples": len(merged),
        "domain_counts": dict(domain_counts),
        "strict_invalid_lines_skipped": strict_invalid_lines,
        "behavior_invalid_lines_skipped": behavior_invalid_lines,
        "notes": [
            "Starts from the clean phase12 strict gold set.",
            "Adds only deduplicated unique rows from qwenf1_train_v2_behavior.",
            "Avoids the older broad qwenf1_train_v1 corpus.",
            "Skips blank or malformed JSONL lines instead of failing the entire build.",
        ],
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
