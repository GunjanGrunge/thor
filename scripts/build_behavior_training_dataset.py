from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

import jsonlines

from common import DATA_DIR, ensure_dir


RNG = random.Random(20260416)

REJECT_SUBSTRINGS = [
    "question_order:",
    "screening_questions:",
    "reference:",
    "source:",
    "section:",
    "sections:",
    "intended_audience:",
    ":section_",
    "how can i assist you?",
]

REQUIRED_BEHAVIOR_HINTS = [
    "before",
    "need",
    "help me tailor",
    "to tailor",
    "because",
]


def clean_text(value: str) -> str:
    replacements = {
        "\u00a0": " ",
        "Ã‚": "",
        "Ã¯Â¿Â½": "'",
        "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢": "'",
        "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“": "-",
        "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬\u009d": "-",
        "ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ": '"',
        "ÃƒÂ¢Ã¢â€šÂ¬\u009d": '"',
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return " ".join(value.split()).strip()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with jsonlines.open(path, mode="r") as reader:
        return list(reader)


def minimalize(example: dict[str, Any], variant: str) -> dict[str, Any]:
    cleaned = json.loads(json.dumps(example))
    for message in cleaned.get("messages", []):
        if isinstance(message.get("content"), str):
            message["content"] = clean_text(message["content"])
    metadata = cleaned.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["training_split"] = "train"
    metadata["dataset_variant"] = variant
    if "domain" not in metadata and isinstance(cleaned.get("domain"), str):
        metadata["domain"] = clean_text(cleaned["domain"])
    if "record_id" not in metadata and isinstance(cleaned.get("id"), str):
        metadata["record_id"] = clean_text(cleaned["id"])
    return {"messages": cleaned.get("messages", []), "metadata": metadata}


def is_behavior_example(example: dict[str, Any]) -> bool:
    messages = example.get("messages", [])
    if len(messages) != 3:
        return False
    if [m.get("role") for m in messages] != ["system", "user", "assistant"]:
        return False

    assistant = messages[2].get("content", "")
    if not isinstance(assistant, str):
        return False
    assistant = clean_text(assistant)
    if not assistant or len(assistant) < 160 or len(assistant) > 5000:
        return False

    assistant_lower = assistant.lower()
    if any(marker in assistant_lower for marker in REJECT_SUBSTRINGS):
        return False
    if assistant.count("[") == 0 or assistant.count("]") == 0:
        return False
    if "?" not in assistant:
        return False
    if not any(hint in assistant_lower for hint in REQUIRED_BEHAVIOR_HINTS):
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--grounded-input",
        default=str(DATA_DIR / "sft" / "grounded_examples_train_ready_bedrock_gemma3_4b_merged.jsonl"),
    )
    parser.add_argument(
        "--output",
        default=str(DATA_DIR / "sft" / "final" / "qwenf1_train_v2_behavior.jsonl"),
    )
    parser.add_argument(
        "--manifest",
        default=str(DATA_DIR / "sft" / "final" / "qwenf1_train_v2_behavior_manifest.json"),
    )
    args = parser.parse_args()

    grounded = load_jsonl(Path(args.grounded_input))
    kept = [minimalize(item, "grounded_behavior_v2") for item in grounded if is_behavior_example(item)]
    RNG.shuffle(kept)

    output_path = Path(args.output)
    ensure_dir(output_path.parent)
    with jsonlines.open(output_path, mode="w") as writer:
        writer.write_all(kept)

    domain_counter: Counter[str] = Counter()
    for item in kept:
        domain_counter[str(item.get("metadata", {}).get("domain", "unknown"))] += 1

    manifest = {
        "input_grounded_examples": len(grounded),
        "kept_behavior_examples": len(kept),
        "rejected_examples": len(grounded) - len(kept),
        "domain_counts": dict(domain_counter),
        "dataset_variant": "grounded_behavior_v2",
        "output_path": str(output_path.as_posix()).replace(str(DATA_DIR.parent.as_posix()) + "/", ""),
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
