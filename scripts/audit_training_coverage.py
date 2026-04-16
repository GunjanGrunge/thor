from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonlines

from common import DATA_DIR


def flatten_content(value: Any) -> list[str]:
    rows: list[str] = []
    if value is None:
        return rows
    if isinstance(value, dict):
        for item in value.values():
            rows.extend(flatten_content(item))
        return rows
    if isinstance(value, list):
        for item in value:
            rows.extend(flatten_content(item))
        return rows
    text = " ".join(str(value).split()).strip()
    if text:
        rows.append(text)
    return rows


def load_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normalized", default=str(DATA_DIR / "normalized" / "evidence_all.jsonl"))
    parser.add_argument("--covered-ids", default=str(DATA_DIR / "sft" / "standalone" / "covered_record_ids.json"))
    parser.add_argument("--report", default=str(DATA_DIR / "sft" / "standalone" / "coverage_audit.json"))
    args = parser.parse_args()

    covered_ids = load_ids(Path(args.covered_ids))
    total = 0
    covered = 0
    missing_ids: list[str] = []
    empty_text_ids: list[str] = []
    domain_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    record_type_counter: Counter[str] = Counter()
    text_rows_total = 0

    with jsonlines.open(args.normalized, mode="r") as reader:
        for record in reader:
            total += 1
            record_id = record["id"]
            domain_counter[record["domain"]] += 1
            source_counter[record["source"]] += 1
            record_type_counter[record["record_type"]] += 1

            rows = []
            for field in [record.get("title"), record.get("summary")]:
                if field:
                    rows.append(" ".join(str(field).split()).strip())
            rows.extend(flatten_content(record.get("content", {})))
            non_empty_rows = [row for row in rows if row]
            text_rows_total += len(non_empty_rows)
            if not non_empty_rows:
                empty_text_ids.append(record_id)

            if record_id in covered_ids:
                covered += 1
            else:
                missing_ids.append(record_id)

    summary = {
        "normalized_records": total,
        "covered_records": covered,
        "missing_records": len(missing_ids),
        "coverage_ratio": round(covered / total, 6) if total else 0.0,
        "records_with_no_text_rows": len(empty_text_ids),
        "total_text_rows_detected": text_rows_total,
        "domains": dict(domain_counter),
        "sources": dict(source_counter),
        "record_types": dict(record_type_counter),
        "missing_record_ids": missing_ids[:200],
        "records_with_no_text_rows_ids": empty_text_ids[:200],
    }

    Path(args.report).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
