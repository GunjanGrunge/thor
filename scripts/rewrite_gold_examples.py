from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import jsonlines


REPLACEMENTS = {
    "�": "-",
    "ï¿½": "-",
    "\ufffd": "-",
    "â€™": "'",
    "â€“": "-",
    "â€œ": '"',
    "â€": '"',
    "â€”": "-",
}


def clean_text(value: str) -> str:
    text = value or ""
    for source, target in REPLACEMENTS.items():
        text = text.replace(source, target)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" - ", " - ")
    return text


def rewrite_assistant(text: str) -> str:
    text = clean_text(text)
    text = text.replace("I can't safely guide you without knowing that your doctor has given the green light.", "I want to know whether your doctor has cleared you for exercise so I can keep the plan within a safe starting range.")
    text = text.replace("As a clinician, my priority is ensuring your safety and well-being [1].", "My priority is keeping your return to exercise safe and individualized [1].")
    text = text.replace("Why this matters:", "This matters because")
    text = text.replace("why this matters:", "this matters because")
    text = re.sub(
        r"Consider creatine supplementation at about 1 g/day-vegetarians have lower baseline muscle creatine stores and respond well to supplementation \[1\]\.",
        "Creatine may be worth considering because vegetarians often start with lower muscle creatine stores, but I would want to confirm your diet pattern and goals before getting specific about dose [1].",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bcreatine supplementation increases serum creatinine levels\b",
        "creatine use can increase serum creatinine levels",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"have you discussed creatine supplementation with your nephrologist",
        "have you discussed this supplement with your nephrologist",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bdo not start creatine until you've had that conversation with your nephrologist\b",
        "hold off on this supplement until you've had that conversation with your nephrologist",
        text,
        flags=re.IGNORECASE,
    )
    if not any(marker in text.lower() for marker in ("for now", "once i have", "before i can", "this matters because")):
        text += " This matters because the right starting plan depends on those answers, not on a generic template."
    text = re.sub(r"\b0-10\b", "0-10", text)
    return text


def dedupe_retrieved_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        urls = [clean_text(url) for url in item.get("grounding_urls", []) if isinstance(url, str) and clean_text(url)]
        unique_urls = [url for url in urls if url not in seen_urls]
        if urls and not unique_urls:
            continue
        row = json.loads(json.dumps(item))
        if unique_urls:
            row["grounding_urls"] = unique_urls
            seen_urls.update(unique_urls)
        deduped.append(row)
    return deduped


def rewrite_example(example: dict[str, Any]) -> dict[str, Any]:
    row = json.loads(json.dumps(example))
    for message in row.get("messages", []):
        content = message.get("content")
        if not isinstance(content, str):
            continue
        if message.get("role") == "assistant":
            message["content"] = rewrite_assistant(content)
        else:
            message["content"] = clean_text(content)

    for point_key in ("screening_points",):
        cleaned_points = []
        for point in row.get(point_key, []) or []:
            if isinstance(point, str):
                cleaned_points.append(clean_text(point))
        row[point_key] = cleaned_points

    for item in row.get("evidence_used", []) or []:
        if isinstance(item, dict):
            for key in ("source", "title", "url"):
                if isinstance(item.get(key), str):
                    item[key] = clean_text(item[key])

    for item in row.get("retrieved_evidence", []) or []:
        if isinstance(item, dict):
            for key in ("source", "title", "text"):
                if isinstance(item.get(key), str):
                    item[key] = clean_text(item[key])
            if isinstance(item.get("grounding_urls"), list):
                item["grounding_urls"] = [clean_text(url) for url in item["grounding_urls"] if isinstance(url, str)]
    row["retrieved_evidence"] = dedupe_retrieved_evidence(row.get("retrieved_evidence", []) or [])

    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    with jsonlines.open(Path(args.input), mode="r") as reader:
        rows = [rewrite_example(row) for row in reader]

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with jsonlines.open(Path(args.output), mode="w") as writer:
        writer.write_all(rows)

    print(json.dumps({"input": args.input, "output": args.output, "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
