from __future__ import annotations

import json
from pathlib import Path

import jsonlines

from common import DATA_DIR


SYSTEM_PROMPT = (
    "You are a fitness and nutrition assistant. Provide practical, safe, "
    "evidence-aware guidance for workouts, nutrition, recovery, and supplements. "
    "Do not claim to diagnose, treat, or replace a medical professional."
)


def normalized_to_examples(path: Path, domain: str) -> list[dict]:
    examples: list[dict] = []
    with jsonlines.open(path, mode="r") as reader:
        for record in reader:
            title = record["title"]
            content = json.dumps(record["content"], ensure_ascii=False)
            user = f"Teach me about {title}."
            assistant = (
                f"Here is a structured overview based on {record['source']}.\n\n"
                f"{content}"
            )
            examples.append(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user},
                        {"role": "assistant", "content": assistant},
                    ],
                    "metadata": {
                        "domain": domain,
                        "source": record["source"],
                        "title": title,
                    },
                }
            )
    return examples


def main() -> None:
    mapping = {
        "supplements": DATA_DIR / "normalized" / "supplements_nih_ods.jsonl",
    }
    combined: list[dict] = []
    for domain, path in mapping.items():
        if not path.exists():
            continue
        records = normalized_to_examples(path, domain)
        out_path = DATA_DIR / "sft" / f"{domain}_seed.jsonl"
        with jsonlines.open(out_path, mode="w") as writer:
            writer.write_all(records)
        print(f"wrote {len(records)} records to {out_path}")
        combined.extend(records)

    dsld_path = DATA_DIR / "normalized" / "supplements_dsld.jsonl"
    if dsld_path.exists():
        dsld_records = normalized_to_examples(dsld_path, "supplements")
        dsld_out_path = DATA_DIR / "sft" / "supplements_dsld_seed.jsonl"
        with jsonlines.open(dsld_out_path, mode="w") as writer:
            writer.write_all(dsld_records)
        print(f"wrote {len(dsld_records)} records to {dsld_out_path}")
        combined.extend(dsld_records)

    for existing_path in [
        DATA_DIR / "sft" / "hf_workout.jsonl",
        DATA_DIR / "sft" / "hf_nutrition.jsonl",
    ]:
        if not existing_path.exists():
            continue
        with jsonlines.open(existing_path, mode="r") as reader:
            combined.extend(list(reader))

    combined_path = DATA_DIR / "sft" / "qwenf1_seed_all.jsonl"
    with jsonlines.open(combined_path, mode="w") as writer:
        writer.write_all(combined)
    print(f"wrote {len(combined)} records to {combined_path}")


if __name__ == "__main__":
    main()
