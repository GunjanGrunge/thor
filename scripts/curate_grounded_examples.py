from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import jsonlines

from validate_grounded_examples import validate_example


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SFT_DIR = DATA_DIR / "sft"


def find_citation_numbers(text: str) -> list[int]:
    import re

    return sorted({int(match) for match in re.findall(r"\[(\d+)\]", text or "")})


def clean_screening_points(points: list[Any]) -> list[str]:
    cleaned: list[str] = []
    seen = set()
    for point in points or []:
        if not isinstance(point, str):
            continue
        value = " ".join(point.split()).strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
    return cleaned


def build_retrieved_index(example: dict[str, Any]) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for idx, item in enumerate(example.get("retrieved_evidence", []), start=1):
        if not isinstance(item, dict):
            continue
        indexed[idx] = item
    return indexed


def repair_example(example: dict[str, Any]) -> dict[str, Any]:
    repaired = json.loads(json.dumps(example))
    messages = repaired.get("messages", [])
    assistant_text = messages[2].get("content", "") if len(messages) >= 3 else ""
    cited_ids = find_citation_numbers(assistant_text)
    retrieved_index = build_retrieved_index(repaired)

    repaired["screening_points"] = clean_screening_points(repaired.get("screening_points", []))

    used_by_id: dict[int, dict[str, Any]] = {}
    for item in repaired.get("evidence_used", []) or []:
        if not isinstance(item, dict):
            continue
        if "citation_id" not in item:
            continue
        try:
            citation_id = int(item["citation_id"])
        except (TypeError, ValueError):
            continue
        used_by_id[citation_id] = {
            "citation_id": citation_id,
            "source": item.get("source", ""),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
        }

    rebuilt_evidence = []
    for citation_id in cited_ids:
        if citation_id in used_by_id:
            rebuilt_evidence.append(used_by_id[citation_id])
            continue
        retrieved = retrieved_index.get(citation_id)
        if not retrieved:
            continue
        rebuilt_evidence.append(
            {
                "citation_id": citation_id,
                "source": retrieved.get("source", ""),
                "title": retrieved.get("title", ""),
                "url": (retrieved.get("grounding_urls") or [""])[0],
            }
        )

    repaired["evidence_used"] = rebuilt_evidence
    return repaired


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(SFT_DIR / "grounded_examples.jsonl"))
    parser.add_argument("--curated-output", default=str(SFT_DIR / "grounded_examples_curated.jsonl"))
    parser.add_argument("--train-output", default=str(SFT_DIR / "grounded_examples_train_ready.jsonl"))
    parser.add_argument("--rejected-output", default=str(SFT_DIR / "grounded_examples_rejected.jsonl"))
    parser.add_argument("--report", default=str(SFT_DIR / "grounded_examples_curation_report.json"))
    args = parser.parse_args()

    with jsonlines.open(args.input, mode="r") as reader:
        examples = list(reader)

    curated = [repair_example(example) for example in examples]
    reports = [validate_example(example) for example in curated]
    train_ready_ids = {report["id"] for report in reports if report["valid"]}

    with jsonlines.open(args.curated_output, mode="w") as writer:
        writer.write_all(curated)

    with jsonlines.open(args.train_output, mode="w") as writer:
        writer.write_all([example for example in curated if example.get("id") in train_ready_ids])

    with jsonlines.open(args.rejected_output, mode="w") as writer:
        writer.write_all([example for example in curated if example.get("id") not in train_ready_ids])

    summary = {
        "input_examples": len(examples),
        "curated_examples": len(curated),
        "train_ready_examples": sum(1 for report in reports if report["valid"]),
        "rejected_examples": sum(1 for report in reports if not report["valid"]),
        "reports": reports,
    }
    Path(args.report).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
