from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonlines


BAD_MARKERS = [
    "infographic",
    "grounding|role=",
    "qwikai",
    "remembrancement=",
    "generator try it out now",
    "skip to main content",
    "open user menu",
    "some rights reserved",
    "published erratum",
]

ENCODING_MARKERS = [
    "Ã",
    "ï¿½",
    "Â©",
    "â€™",
    "â€œ",
    "â€",
]


def clean_text(value: str) -> str:
    return " ".join(value.split()).strip()


def row_issues(row: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 3:
        return ["bad_message_structure"]

    roles = [message.get("role") for message in messages]
    if roles[:3] != ["system", "user", "assistant"]:
        issues.append("unexpected_role_order")

    assistant = ""
    for message in messages:
        content = message.get("content")
        if not isinstance(content, str) or not clean_text(content):
            issues.append("empty_message")
            continue
        if message.get("role") == "assistant":
            assistant = content

    if not assistant:
        issues.append("missing_assistant")
        return issues

    lowered = assistant.lower()
    for marker in BAD_MARKERS:
        if marker in lowered:
            issues.append(f"bad_marker:{marker}")
    for marker in ENCODING_MARKERS:
        if marker in assistant:
            issues.append(f"encoding:{marker}")

    if len(assistant) > 12000:
        issues.append("assistant_too_long")
    if assistant.count("infographic") >= 3:
        issues.append("repeated_infographic")
    if assistant.count("Title:") > 1:
        issues.append("multiple_title_blocks")

    metadata = row.get("metadata", {})
    if not isinstance(metadata, dict):
        issues.append("missing_metadata")
    else:
        for required in ("domain", "dataset_variant", "training_split"):
            if required not in metadata:
                issues.append(f"missing_metadata:{required}")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--bad-samples", default="")
    args = parser.parse_args()

    path = Path(args.input)
    report_path = Path(args.report)
    bad_samples_path = Path(args.bad_samples) if args.bad_samples else None
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if bad_samples_path is not None:
        bad_samples_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    valid = 0
    invalid = 0
    issue_counter: Counter[str] = Counter()
    bad_rows: list[dict[str, Any]] = []

    with jsonlines.open(path, mode="r") as reader:
        for row in reader:
            total += 1
            issues = row_issues(row)
            if issues:
                invalid += 1
                for issue in issues:
                    issue_counter[issue] += 1
                if len(bad_rows) < 100:
                    bad_rows.append(
                        {
                            "messages": row.get("messages", []),
                            "metadata": row.get("metadata", {}),
                            "issues": issues,
                        }
                    )
            else:
                valid += 1

    report = {
        "input": str(path),
        "total_rows": total,
        "valid_rows": valid,
        "invalid_rows": invalid,
        "invalid_ratio": round(invalid / total, 6) if total else 0.0,
        "issue_counts": dict(issue_counter),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if bad_samples_path is not None:
        with jsonlines.open(bad_samples_path, mode="w") as writer:
            writer.write_all(bad_rows)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
