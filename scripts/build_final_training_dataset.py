from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import jsonlines

from common import DATA_DIR, ensure_dir


RNG = random.Random(20260415)

REJECT_SUBSTRINGS = [
    "infographic\n\ninfographic",
    "infographic.title",
    "grounding|role=",
    "qwikai",
    "remembrancement=",
    "infomercials are not evidence-based",
    "infomation needed",
    "generator try it out now",
    "open user menu",
    "skip to main content",
]


def clean_text(value: str) -> str:
    replacements = {
        "\u00a0": " ",
        "Â": "",
        "ï¿½": "'",
        "Ã¢â‚¬â„¢": "'",
        "Ã¢â‚¬â€œ": "-",
        "Ã¢â‚¬â€\u009d": "-",
        "Ã¢â‚¬Å“": '"',
        "Ã¢â‚¬\u009d": '"',
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return " ".join(value.split()).strip()


def clean_messages(example: dict[str, Any]) -> dict[str, Any]:
    cleaned = json.loads(json.dumps(example))
    for message in cleaned.get("messages", []):
        if isinstance(message.get("content"), str):
            message["content"] = clean_text(message["content"])
    metadata = cleaned.get("metadata", {})
    if isinstance(metadata, dict):
        for key, value in list(metadata.items()):
            if isinstance(value, str):
                metadata[key] = clean_text(value)
            elif isinstance(value, list):
                metadata[key] = [clean_text(item) if isinstance(item, str) else item for item in value]
    # Keep training rows minimal: chat messages + metadata only.
    minimal: dict[str, Any] = {"messages": cleaned.get("messages", [])}
    if isinstance(metadata, dict):
        minimal["metadata"] = metadata
    elif isinstance(cleaned.get("metadata"), dict):
        minimal["metadata"] = cleaned["metadata"]
    else:
        minimal["metadata"] = {}
    return minimal


def is_quality_example(example: dict[str, Any]) -> bool:
    messages = example.get("messages", [])
    if len(messages) < 3:
        return False
    assistant = ""
    for message in messages:
        content = message.get("content")
        if not isinstance(content, str) or not clean_text(content):
            return False
        if message.get("role") == "assistant":
            assistant = clean_text(content)
    if not assistant:
        return False

    assistant_lower = assistant.lower()
    if any(marker in assistant_lower for marker in REJECT_SUBSTRINGS):
        return False
    if len(assistant) > 12000:
        return False
    if assistant_lower.count("infographic") >= 3:
        return False
    if assistant_lower.count("title:") > 1:
        return False
    return True


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with jsonlines.open(path, mode="r") as reader:
        return [item for item in reader]


def sample_group(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if len(records) <= limit:
        return records
    return RNG.sample(records, limit)


def annotate(records: list[dict[str, Any]], split: str, variant: str) -> list[dict[str, Any]]:
    annotated = []
    for record in records:
        item = clean_messages(record)
        if not is_quality_example(item):
            continue
        metadata = item.setdefault("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
            item["metadata"] = metadata
        if "domain" not in metadata:
            if "domain" in item:
                metadata["domain"] = item.get("domain")
            else:
                metadata["domain"] = "unknown"
        metadata["training_split"] = split
        metadata["dataset_variant"] = variant
        # Preserve source id/domain hints if they existed outside metadata.
        if "record_id" not in metadata and isinstance(record.get("id"), str):
            metadata["record_id"] = clean_text(record["id"])
        if "domain" not in metadata and isinstance(record.get("domain"), str):
            metadata["domain"] = clean_text(record["domain"])
        annotated.append(item)
    return annotated


def build_standalone_mix(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    by_domain: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        domain = str(record.get("metadata", {}).get("domain", "unknown"))
        by_domain[domain].append(record)

    targets = {
        "nutrition": 4000,
        "supplements": 536,
        "workout": 1700,
        "guidelines": 18,
        "science": 3000,
    }

    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for domain, group in by_domain.items():
        chosen = sample_group(group, targets.get(domain, len(group)))
        counts[domain] = len(chosen)
        selected.extend(chosen)
    RNG.shuffle(selected)
    return selected, counts


def build_seed_mix() -> list[dict[str, Any]]:
    paths = [
        DATA_DIR / "sft" / "hf_nutrition.jsonl",
        DATA_DIR / "sft" / "hf_workout.jsonl",
        DATA_DIR / "sft" / "supplements_seed.jsonl",
        DATA_DIR / "sft" / "supplements_dsld_seed.jsonl",
    ]
    combined: list[dict[str, Any]] = []
    for path in paths:
        combined.extend(load_jsonl(path))
    return combined


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--standalone-input", default=str(DATA_DIR / "sft" / "standalone" / "standalone_knowledge_all.jsonl"))
    parser.add_argument("--grounded-input", default=str(DATA_DIR / "sft" / "grounded_examples_train_ready_bedrock_gemma3_4b_merged.jsonl"))
    parser.add_argument("--output-dir", default=str(DATA_DIR / "sft" / "final"))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    standalone_all = load_jsonl(Path(args.standalone_input))
    grounded = load_jsonl(Path(args.grounded_input))
    seeds = build_seed_mix()

    standalone_selected, standalone_counts = build_standalone_mix(standalone_all)

    standalone_annotated = annotate(standalone_selected, "train", "standalone_knowledge")
    grounded_annotated = annotate(grounded, "train", "grounded_train_ready")
    seed_annotated = annotate(seeds, "train", "seed_corpus")

    final_records: list[dict[str, Any]] = []
    final_records.extend(standalone_annotated)
    final_records.extend(grounded_annotated)
    final_records.extend(seed_annotated)

    RNG.shuffle(final_records)

    output_path = output_dir / "qwenf1_train_v1.jsonl"
    with jsonlines.open(output_path, mode="w") as writer:
        writer.write_all(final_records)

    full_coverage_records: list[dict[str, Any]] = []
    full_coverage_records.extend(annotate(standalone_all, "train", "standalone_knowledge_full"))
    full_coverage_records.extend(grounded_annotated)
    full_coverage_records.extend(seed_annotated)
    RNG.shuffle(full_coverage_records)

    full_output_path = output_dir / "qwenf1_train_v1_fullcoverage.jsonl"
    with jsonlines.open(full_output_path, mode="w") as writer:
        writer.write_all(full_coverage_records)

    variant_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    for record in final_records:
        metadata = record.get("metadata", {})
        variant_counter[str(metadata.get("dataset_variant", "unknown"))] += 1
        domain_counter[str(metadata.get("domain", "unknown"))] += 1

    manifest = {
        "output_examples_balanced": len(final_records),
        "output_examples_fullcoverage": len(full_coverage_records),
        "standalone_selected": len(standalone_selected),
        "standalone_fullcoverage": len(standalone_all),
        "grounded_selected": len(grounded),
        "seed_selected": len(seeds),
        "standalone_domain_counts": standalone_counts,
        "final_domain_counts": dict(domain_counter),
        "final_variant_counts": dict(variant_counter),
        "knowledge_cutoff": "2026-04-15",
        "output_path": "data/sft/final/qwenf1_train_v1.jsonl",
        "fullcoverage_output_path": "data/sft/final/qwenf1_train_v1_fullcoverage.jsonl",
    }
    (output_dir / "qwenf1_train_v1_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
