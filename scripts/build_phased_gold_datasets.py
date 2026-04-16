from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonlines


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with jsonlines.open(path, mode="r") as reader:
        return list(reader)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with jsonlines.open(path, mode="w") as writer:
        writer.write_all(rows)


def minimalize(example: dict[str, Any], variant: str) -> dict[str, Any]:
    return {
        "messages": example.get("messages", []),
        "metadata": {
            "training_split": "train",
            "dataset_variant": variant,
            "domain": example.get("domain", example.get("metadata", {}).get("domain", "unknown")),
            "record_id": example.get("id", example.get("metadata", {}).get("record_id", "")),
        },
    }


def summarize_domains(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter[row.get("domain", row.get("metadata", {}).get("domain", "unknown"))] += 1
    return dict(counter)


def summarize_rewrite_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for row in rows:
        queue.append(
            {
                "id": row.get("id"),
                "domain": row.get("domain", "unknown"),
                "screening_points": row.get("screening_points", []),
                "evidence_count": len(row.get("evidence_used", [])),
                "retrieved_count": len(row.get("retrieved_evidence", [])),
            }
        )
    return queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-input", required=True)
    parser.add_argument("--rewrite-input", required=True)
    parser.add_argument("--reject-input", required=True)
    parser.add_argument("--phase1-output", required=True)
    parser.add_argument("--rewrite-queue-output", required=True)
    parser.add_argument("--manifest-output", required=True)
    args = parser.parse_args()

    keep_rows = load_jsonl(Path(args.keep_input))
    rewrite_rows = load_jsonl(Path(args.rewrite_input))
    reject_rows = load_jsonl(Path(args.reject_input))

    phase1_rows = [minimalize(row, "grounded_behavior_phase1_strict_gold") for row in keep_rows]
    write_jsonl(Path(args.phase1_output), phase1_rows)

    rewrite_queue = summarize_rewrite_queue(rewrite_rows)
    Path(args.rewrite_queue_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.rewrite_queue_output).write_text(json.dumps(rewrite_queue, indent=2), encoding="utf-8")

    manifest = {
        "phase1": {
            "dataset": args.phase1_output,
            "examples": len(phase1_rows),
            "domain_counts": summarize_domains(keep_rows),
            "status": "trainable_strict_seed_only",
            "note": "Use only for a low-cost sanity-check run, not for a production-quality full fine-tune.",
        },
        "phase2": {
            "rewrite_queue": args.rewrite_queue_output,
            "examples": len(rewrite_rows),
            "domain_counts": summarize_domains(rewrite_rows),
            "status": "rewrite_required",
            "note": "These examples are salvageable but should not be trained before rewrite and re-QC.",
        },
        "phase3": {
            "regenerate_examples": len(reject_rows),
            "domain_counts": summarize_domains(reject_rows),
            "status": "regenerate",
            "note": "These examples failed gold-QC and should be regenerated, not patched into training.",
            "record_ids": [row.get("id") for row in reject_rows],
        },
        "full_batch": {
            "keep": len(keep_rows),
            "needs_rewrite": len(rewrite_rows),
            "reject": len(reject_rows),
            "go_no_go": "no_go_for_expensive_training",
        },
    }
    Path(args.manifest_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.manifest_output).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
