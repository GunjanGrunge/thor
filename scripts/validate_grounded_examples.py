from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import jsonlines


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SFT_DIR = DATA_DIR / "sft"


FIXED_SYSTEM = "You are a fitness and nutrition assistant grounded in evidence-based exercise physiology and sports nutrition."
REJECT_OUTPUT_MARKERS = [
    "question_order:",
    "screening_questions:",
    "title:",
    "reference:",
    "source:",
    "section:",
    "sections:",
    "intended_audience:",
    ":section_",
    "how can i assist you?",
]


def find_citation_numbers(text: str) -> set[int]:
    return {int(match) for match in re.findall(r"\[(\d+)\]", text or "")}


def build_retrieved_url_set(example: dict[str, Any]) -> set[str]:
    urls = set()
    for item in example.get("retrieved_evidence", []):
        if not isinstance(item, dict):
            continue
        for url in item.get("grounding_urls", []):
            if url:
                urls.add(url)
    return urls


def obvious_population_mismatch(user_text: str, title: str, snippet: str) -> bool:
    user_lower = user_text.lower()
    combined = f"{title} {snippet}".lower()
    if "adult" in user_lower or "older" in user_lower or "postpartum" in user_lower:
        if any(token in combined for token in ["children", "child", "adolescent", "youth"]):
            return True
    return False


def validate_example(example: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    warnings: list[str] = []

    messages = example.get("messages", [])
    if len(messages) != 3:
        findings.append("messages must contain exactly 3 entries")
    else:
        if messages[0].get("role") != "system" or messages[0].get("content") != FIXED_SYSTEM:
            findings.append("system message is not the fixed evidence-grounded instruction")
        if messages[1].get("role") != "user":
            findings.append("second message must be the user message")
        if messages[2].get("role") != "assistant":
            findings.append("third message must be the assistant message")

    assistant_text = messages[2].get("content") if len(messages) >= 3 else ""
    if not isinstance(assistant_text, str):
        assistant_text = ""
    cited_in_text = find_citation_numbers(assistant_text)
    evidence_used = [item for item in (example.get("evidence_used", []) or []) if isinstance(item, dict)]
    evidence_ids = {int(item["citation_id"]) for item in evidence_used if "citation_id" in item}
    retrieved_urls = build_retrieved_url_set(example)
    user_text = messages[1].get("content") if len(messages) >= 2 else ""
    if not isinstance(user_text, str):
        user_text = ""

    if not assistant_text.strip():
        findings.append("assistant response is empty")
    assistant_lower = assistant_text.lower()
    if any(marker in assistant_lower for marker in REJECT_OUTPUT_MARKERS):
        findings.append("assistant response contains schema-like or placeholder output")
    if "?" not in assistant_text:
        findings.append("assistant response does not ask any screening question")
    if not any(token in assistant_lower for token in ["before", "because", "to tailor", "need to know", "help me tailor"]):
        warnings.append("assistant may not explain why screening matters")
    screening_points = example.get("screening_points") or []
    non_empty_screening_points = [point for point in screening_points if isinstance(point, str) and point.strip()]
    if not non_empty_screening_points:
        findings.append("screening_points is empty")
    if len(non_empty_screening_points) < 3 or len(non_empty_screening_points) > 6:
        findings.append("screening_points must contain 3 to 6 items")
    if not evidence_used:
        findings.append("evidence_used is empty")

    missing_in_text = evidence_ids - cited_in_text
    if missing_in_text:
        findings.append(f"citations declared but not used inline: {sorted(missing_in_text)}")

    extra_in_text = cited_in_text - evidence_ids
    if extra_in_text:
        findings.append(f"inline citations missing from evidence_used: {sorted(extra_in_text)}")

    for item in evidence_used:
        url = item.get("url", "")
        if url and url not in retrieved_urls:
            findings.append(f"evidence_used URL not found in retrieved evidence: {url}")

    screening_text = " ".join(point.lower() for point in non_empty_screening_points)
    if any(token in user_text.lower() for token in ["blood pressure", "hypertension", "diabetes", "postpartum", "pregnan"]):
        expected = []
        if any(token in user_text.lower() for token in ["blood pressure", "hypertension"]):
            expected = ["medication", "symptom", "clearance"]
        elif "diabetes" in user_text.lower():
            expected = ["medication", "hypogly", "neurop", "retin"]
        elif any(token in user_text.lower() for token in ["postpartum", "pregnan"]):
            expected = ["clearance", "symptom", "pelvic", "delivery"]
        if expected and not any(token in screening_text for token in expected):
            warnings.append("condition-specific screening may be too weak")

    for item in example.get("retrieved_evidence", []):
        if not isinstance(item, dict):
            continue
        title = item.get("title", "")
        snippet = item.get("text", "")
        if obvious_population_mismatch(user_text, title, snippet):
            warnings.append(f"retrieved evidence may be population-mismatched: {title}")

    return {
        "id": example.get("id"),
        "valid": len(findings) == 0,
        "findings": findings,
        "warnings": sorted(set(warnings)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(SFT_DIR / "grounded_examples.jsonl"))
    parser.add_argument("--report", default=str(SFT_DIR / "grounded_examples_validation.json"))
    parser.add_argument("--valid-output", default=str(SFT_DIR / "grounded_examples_valid.jsonl"))
    parser.add_argument("--invalid-output", default=str(SFT_DIR / "grounded_examples_invalid.jsonl"))
    args = parser.parse_args()

    examples = []
    with jsonlines.open(args.input, mode="r") as reader:
        examples = list(reader)

    reports = [validate_example(example) for example in examples]
    valid_ids = {report["id"] for report in reports if report["valid"]}

    with jsonlines.open(args.valid_output, mode="w") as writer:
        writer.write_all([example for example in examples if example.get("id") in valid_ids])

    with jsonlines.open(args.invalid_output, mode="w") as writer:
        writer.write_all([example for example in examples if example.get("id") not in valid_ids])

    summary = {
        "input_examples": len(examples),
        "valid_examples": sum(1 for report in reports if report["valid"]),
        "invalid_examples": sum(1 for report in reports if not report["valid"]),
        "reports": reports,
    }
    Path(args.report).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
