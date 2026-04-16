from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from common import DATA_DIR, stable_id, write_jsonl


HEADER_PATTERN = re.compile(
    r"<\|start_header_id\|>(?P<role>.*?)<\|end_header_id\|>(?P<content>.*?)<\|eot_id\|>",
    re.DOTALL,
)


def parse_header_prompt(prompt: str) -> list[dict[str, str]] | None:
    messages: list[dict[str, str]] = []
    for match in HEADER_PATTERN.finditer(prompt):
        role = match.group("role").strip()
        content = match.group("content").strip()
        if not content:
            continue
        if role not in {"system", "user", "assistant"}:
            continue
        messages.append({"role": role, "content": content})
    return messages or None


def extract_messages(row: dict[str, Any]) -> list[dict[str, str]] | None:
    if isinstance(row.get("messages"), list):
        messages = []
        for message in row["messages"]:
            role = message.get("role")
            content = message.get("content")
            if role and content:
                messages.append({"role": str(role), "content": str(content)})
        return messages or None

    if isinstance(row.get("conversations"), list):
        messages = []
        role_map = {"user": "user", "assistant": "assistant", "system": "system"}
        for message in row["conversations"]:
            role = role_map.get(str(message.get("from", "")).strip().lower())
            content = message.get("value")
            if role and content:
                messages.append({"role": role, "content": str(content)})
        return messages or None

    if row.get("prompt") and "<|start_header_id|>" in str(row["prompt"]):
        return parse_header_prompt(str(row["prompt"]))

    if row.get("instruction") and row.get("output"):
        prompt = str(row["instruction"])
        if row.get("input"):
            prompt = f"{prompt}\n\nContext:\n{row['input']}"
        return [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": str(row["output"])},
        ]

    for user_key, assistant_key in [
        ("prompt", "response"),
        ("question", "answer"),
        ("query", "response"),
    ]:
        if row.get(user_key) and row.get(assistant_key):
            return [
                {"role": "user", "content": str(row[user_key])},
                {"role": "assistant", "content": str(row[assistant_key])},
            ]
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-name", required=True)
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()

    raw_path = DATA_DIR / "raw" / args.input_name / "rows.json"
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    dataset_name = payload["dataset"]
    normalized_records: list[dict] = []
    sft_records: list[dict] = []

    for item in payload["rows"]:
        row = item.get("row", {})
        messages = extract_messages(row)
        if not messages:
            continue
        sample_id = stable_id(args.input_name, json.dumps(row, sort_keys=True, ensure_ascii=False))
        normalized_records.append(
            {
                "id": sample_id,
                "domain": args.domain,
                "source": dataset_name,
                "record_type": "chat_example",
                "title": f"{args.domain} sample",
                "content": {"messages": messages},
                "tags": [args.domain, "chat"],
                "grounding_urls": [f"https://huggingface.co/datasets/{dataset_name}"],
            }
        )
        sft_records.append(
            {
                "messages": messages,
                "metadata": {
                    "domain": args.domain,
                    "source": dataset_name,
                    "id": sample_id,
                },
            }
        )

    write_jsonl(DATA_DIR / "normalized" / f"{args.input_name}.jsonl", normalized_records)
    write_jsonl(DATA_DIR / "sft" / f"{args.input_name}.jsonl", sft_records)
    print(f"wrote {len(normalized_records)} normalized and {len(sft_records)} sft rows")


if __name__ == "__main__":
    main()
