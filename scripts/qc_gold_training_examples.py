from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import jsonlines


ENCODING_MARKERS = [
    "ï¿½",
    "\ufffd",
    "Ã",
    "â€™",
    "â€“",
    "â€œ",
    "â€",
]

RETRIEVAL_NOISE_MARKERS = [
    "subscribe sign in",
    "site updates",
    "feedback question",
    "premium store",
    "about us testimonies",
    "open user menu",
    "skip to main content",
]

ROLE_CONFUSION_MARKERS = [
    "as a clinician",
    "my priority is ensuring your safety",
    "i can't safely guide you without",
    "i cannot safely guide you without",
    "i need your doctor to",
]

SUPPLEMENT_SPECIFICITY_PATTERNS = [
    re.compile(r"\bcreatine\b.{0,40}\b(?:1|2|3|4|5)\s?g/day", re.IGNORECASE),
    re.compile(r"\b(?:take|use|start)\b.{0,20}\bcreatine\b", re.IGNORECASE),
]

CONDITION_TOKENS = [
    "hypertension",
    "blood pressure",
    "diabetes",
    "prediabetes",
    "postpartum",
    "pcos",
    "osteoarthritis",
    "back pain",
    "kidney disease",
    "cardiac",
    "heart procedure",
]


def clean_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with jsonlines.open(path, mode="r") as reader:
        return list(reader)


def assistant_text(example: dict[str, Any]) -> str:
    for message in example.get("messages", []):
        if message.get("role") == "assistant" and isinstance(message.get("content"), str):
            return message["content"]
    return ""


def user_text(example: dict[str, Any]) -> str:
    for message in example.get("messages", []):
        if message.get("role") == "user" and isinstance(message.get("content"), str):
            return message["content"]
    return ""


def count_noise_chunks(retrieved_evidence: list[dict[str, Any]]) -> int:
    count = 0
    for item in retrieved_evidence:
        text = clean_text(str(item.get("text", ""))).lower()
        if any(marker in text for marker in RETRIEVAL_NOISE_MARKERS):
            count += 1
    return count


def duplicate_url_ratio(retrieved_evidence: list[dict[str, Any]]) -> float:
    urls: list[str] = []
    for item in retrieved_evidence:
        for url in item.get("grounding_urls", []):
            if url:
                urls.append(url)
    if not urls:
        return 0.0
    most_common = Counter(urls).most_common(1)[0][1]
    return most_common / len(urls)


def retrieval_source_mix(retrieved_evidence: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in retrieved_evidence:
        source = str(item.get("source", "unknown")).lower()
        counter[source] += 1
    return counter


def minimalize(example: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        "training_split": "train",
        "dataset_variant": "grounded_behavior_gold_candidate",
        "domain": example.get("domain", example.get("metadata", {}).get("domain", "unknown")),
        "record_id": example.get("id", example.get("metadata", {}).get("record_id", "")),
    }
    return {"messages": example.get("messages", []), "metadata": metadata}


def classify(example: dict[str, Any]) -> dict[str, Any]:
    user = clean_text(user_text(example))
    assistant = clean_text(assistant_text(example))
    retrieved = [item for item in example.get("retrieved_evidence", []) if isinstance(item, dict)]
    evidence_used = [item for item in example.get("evidence_used", []) if isinstance(item, dict)]
    issues: list[str] = []
    warnings: list[str] = []

    if not assistant:
        issues.append("empty_assistant")

    lowered_assistant = assistant.lower()
    lowered_user = user.lower()

    if any(marker in assistant for marker in ENCODING_MARKERS):
        issues.append("encoding_artifacts")

    for marker in ROLE_CONFUSION_MARKERS:
        if marker in lowered_assistant:
            issues.append("role_confusion")
            break

    if not any(ch in assistant for ch in ("?",)):
        issues.append("missing_screening_question")

    if not any(token in lowered_assistant for token in ["for now", "once i have", "before i can", "this matters because"]):
        warnings.append("weak_screening_rationale")

    if any(token in lowered_user for token in CONDITION_TOKENS):
        source_mix = retrieval_source_mix(retrieved)
        if source_mix.get("exrx", 0) >= 2:
            warnings.append("condition_query_contains_exrx_noise")
        if count_noise_chunks(retrieved) >= 1:
            warnings.append("noisy_retrieval_chunks")

    dup_ratio = duplicate_url_ratio(retrieved)
    if dup_ratio >= 0.8 and len(retrieved) >= 4:
        warnings.append("retrieval_overconcentrated_single_url")

    if len(evidence_used) == 0:
        issues.append("no_evidence_used")

    if len(evidence_used) > 3:
        issues.append("too_many_citations")

    if "creatine" in lowered_assistant:
        for pattern in SUPPLEMENT_SPECIFICITY_PATTERNS:
            if pattern.search(assistant):
                warnings.append("specific_supplement_dose_claim")
                break

    decision = "keep"
    if issues:
        decision = "reject"
    elif warnings:
        decision = "needs_rewrite"

    return {
        "id": example.get("id"),
        "domain": example.get("domain"),
        "decision": decision,
        "issues": sorted(set(issues)),
        "warnings": sorted(set(warnings)),
        "assistant_preview": assistant[:500],
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with jsonlines.open(path, mode="w") as writer:
        writer.write_all(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--keep-output", required=True)
    parser.add_argument("--rewrite-output", required=True)
    parser.add_argument("--reject-output", required=True)
    parser.add_argument("--gold-output", required=True)
    args = parser.parse_args()

    examples = load_jsonl(Path(args.input))
    reviews = [classify(example) for example in examples]
    by_id = {str(example.get("id")): example for example in examples}

    keep_ids = {item["id"] for item in reviews if item["decision"] == "keep"}
    rewrite_ids = {item["id"] for item in reviews if item["decision"] == "needs_rewrite"}
    reject_ids = {item["id"] for item in reviews if item["decision"] == "reject"}

    keep_rows = [by_id[item_id] for item_id in keep_ids if item_id in by_id]
    rewrite_rows = [by_id[item_id] for item_id in rewrite_ids if item_id in by_id]
    reject_rows = [by_id[item_id] for item_id in reject_ids if item_id in by_id]

    write_jsonl(Path(args.keep_output), keep_rows)
    write_jsonl(Path(args.rewrite_output), rewrite_rows)
    write_jsonl(Path(args.reject_output), reject_rows)
    write_jsonl(Path(args.gold_output), [minimalize(row) for row in keep_rows])

    decision_counts = Counter(item["decision"] for item in reviews)
    issue_counts = Counter(issue for item in reviews for issue in item["issues"])
    warning_counts = Counter(warning for item in reviews for warning in item["warnings"])

    report = {
        "input_examples": len(examples),
        "decision_counts": dict(decision_counts),
        "issue_counts": dict(issue_counts),
        "warning_counts": dict(warning_counts),
        "reviews": reviews,
        "gold_output": args.gold_output,
    }
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
