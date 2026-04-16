from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import jsonlines

from common import DATA_DIR, ensure_dir


SYSTEM_PROMPT = (
    "You are QwenF1, an evidence-based exercise physiology and sports nutrition "
    "assistant with a knowledge cutoff of April 15, 2026. Give grounded, cautious, "
    "condition-aware guidance. Do not invent evidence or claim to replace a clinician."
)

SKIP_TITLE_PATTERNS = [
    "infographic:",
    "correction to ",
    "published erratum",
]

SKIP_ROW_PATTERNS = [
    "skip to main content",
    "an official website of the united states government",
    "open user menu",
    "open search",
    "open sidebar",
    "generator try it out now",
    "simplify your workout, anywhere",
    "download musclewiki mobile",
    "app store google play",
    "some rights reserved",
    "terms | privacy policy | api | about",
    "official websites use .gov",
    "secure .gov websites use https",
    "here's how you know",
    "trending search",
    "share this infographic",
    "follow us facebook",
    "call 800-232-4636",
    " infographic ",
    " infographic:",
    " infographic.",
]

BAD_TEXT_PATTERNS = [
    "Ã",
    "ï¿½",
    "Â©",
    "â€™",
    "â€œ",
    "â€",
]


def clean_text(value: str) -> str:
    replacements = {
        "\u00a0": " ",
        "Ã‚": "",
        "Ã¯Â¿Â½": "'",
        "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢": "'",
        "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“": '"',
        "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬\u009d": '"',
        "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬â€œ": "-",
        "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬â€\u009d": "-",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return " ".join(value.split()).strip()


def is_noise_title(title: str) -> bool:
    lowered = title.lower()
    return any(pattern in lowered for pattern in SKIP_TITLE_PATTERNS)


def is_noise_row(text: str) -> bool:
    lowered = f" {text.lower()} "
    return any(pattern in lowered for pattern in SKIP_ROW_PATTERNS)


def has_bad_text(text: str) -> bool:
    return any(pattern in text for pattern in BAD_TEXT_PATTERNS)


def stringify_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    return clean_text(str(value))


def flatten_content(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    if value is None:
        return rows

    if isinstance(value, dict):
        for key, item in value.items():
            key_name = clean_text(str(key))
            if key_name.lower() == "text":
                continue
            next_prefix = f"{prefix}.{key_name}" if prefix else key_name
            rows.extend(flatten_content(item, next_prefix))
        return rows

    if isinstance(value, list):
        for idx, item in enumerate(value, start=1):
            next_prefix = f"{prefix}[{idx}]"
            rows.extend(flatten_content(item, next_prefix))
        return rows

    text = stringify_value(value)
    if text and not is_noise_row(text):
        rows.append((prefix or "value", text))
    return rows


def take_rows(rows: list[tuple[str, str]], limit: int) -> list[tuple[str, str]]:
    return rows[:limit] if len(rows) > limit else rows


def make_user_prompt(record: dict[str, Any]) -> str:
    title = clean_text(record.get("title", "this evidence record"))
    domain = record.get("domain", "combined")
    record_type = record.get("record_type", "reference")

    if record_type == "food_reference":
        return f"What should I know about the nutrition profile of {title}?"
    if "exercise" in record_type:
        return f"How should I understand and use the exercise reference for {title}?"
    if "guideline" in record_type:
        return f"What are the main evidence-based practice points from {title}?"
    if "scientific" in record_type:
        return f"Summarize the evidence and practical takeaway from {title}."
    if domain == "supplements":
        return f"What are the important evidence-based details about {title}?"
    return f"Teach me the key evidence-based facts about {title}."


def make_assistant_text(record: dict[str, Any]) -> tuple[str, int]:
    title = clean_text(record.get("title", "Untitled"))
    summary = clean_text(record.get("summary", "")) or title
    domain = record.get("domain", "combined")
    source = record.get("source", "unknown")
    record_type = record.get("record_type", "reference")
    grounding_urls = record.get("grounding_urls", [])
    content_rows = flatten_content(record.get("content", {}))

    if is_noise_row(summary) or has_bad_text(summary):
        summary = title

    field_limit = 24
    if record_type == "food_reference":
        field_limit = 28
    elif "scientific" in record_type:
        field_limit = 18
    elif "exercise" in record_type:
        field_limit = 20
    elif "guideline" in record_type or domain == "guidelines":
        field_limit = 16

    selected_rows = take_rows(content_rows, field_limit)

    lines = [
        f"Title: {title}",
        f"Domain: {domain}",
        f"Source: {source}",
        f"Record Type: {record_type}",
        f"Summary: {summary}",
        "Key Facts:",
    ]

    for key, value in selected_rows:
        lines.append(f"- {key}: {value}")

    if grounding_urls:
        lines.append("Grounding URLs:")
        for url in grounding_urls[:3]:
            lines.append(f"- {url}")

    return "\n".join(lines), len(selected_rows)


def is_record_usable(record: dict[str, Any]) -> bool:
    title = clean_text(record.get("title", ""))
    summary = clean_text(record.get("summary", ""))
    if not title or not summary:
        return False
    if is_noise_title(title):
        return False
    if has_bad_text(title) or has_bad_text(summary):
        return False

    record_type = str(record.get("record_type", "")).lower()
    metadata = record.get("metadata", {}) or {}
    if metadata.get("page_kind") == "index":
        return False
    if record_type.endswith("directory_page") or record_type.endswith("category_page"):
        return False

    content = record.get("content", {})
    if isinstance(content, dict):
        publication_types = [clean_text(str(item)).lower() for item in content.get("publication_types", [])]
        if "published erratum" in publication_types:
            return False
    return True


def build_examples(input_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    domain_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    record_type_counter: Counter[str] = Counter()
    covered_ids: list[str] = []
    source_rows: defaultdict[str, int] = defaultdict(int)
    skipped_records = 0

    with jsonlines.open(input_path, mode="r") as reader:
        for record in reader:
            if not is_record_usable(record):
                skipped_records += 1
                continue

            assistant_text, extracted_rows = make_assistant_text(record)
            if extracted_rows == 0 or has_bad_text(assistant_text):
                skipped_records += 1
                continue

            metadata = {
                "record_id": record["id"],
                "domain": record["domain"],
                "source": record["source"],
                "record_type": record["record_type"],
                "title": clean_text(record["title"]),
                "knowledge_cutoff": "2026-04-15",
                "grounding_urls": record.get("grounding_urls", []),
                "extracted_row_count": extracted_rows,
            }
            examples.append(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": make_user_prompt(record)},
                        {"role": "assistant", "content": assistant_text},
                    ],
                    "metadata": metadata,
                }
            )
            covered_ids.append(record["id"])
            domain_counter[record["domain"]] += 1
            source_counter[record["source"]] += 1
            record_type_counter[record["record_type"]] += 1
            source_rows[record["source"]] += extracted_rows

    manifest = {
        "input_records": len(examples) + skipped_records,
        "output_examples": len(examples),
        "skipped_records": skipped_records,
        "domains": dict(domain_counter),
        "sources": dict(source_counter),
        "record_types": dict(record_type_counter),
        "extracted_rows_by_source": dict(source_rows),
        "covered_record_ids_path": "data/sft/standalone/covered_record_ids.json",
    }
    return examples, {"manifest": manifest, "covered_ids": covered_ids}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DATA_DIR / "normalized" / "evidence_all.jsonl"))
    parser.add_argument("--output-dir", default=str(DATA_DIR / "sft" / "standalone"))
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    examples, state = build_examples(input_path)

    output_path = output_dir / "standalone_knowledge_all.jsonl"
    with jsonlines.open(output_path, mode="w") as writer:
        writer.write_all(examples)

    (output_dir / "build_manifest.json").write_text(
        json.dumps(state["manifest"], indent=2),
        encoding="utf-8",
    )
    (output_dir / "covered_record_ids.json").write_text(
        json.dumps(state["covered_ids"], indent=2),
        encoding="utf-8",
    )

    print(json.dumps(state["manifest"], indent=2))


if __name__ == "__main__":
    main()
