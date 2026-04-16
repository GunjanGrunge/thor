from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def main() -> None:
    normalized_dir = DATA_DIR / "normalized"
    ingestion_dir = DATA_DIR / "ingestion"
    embeddings_dir = DATA_DIR / "embeddings" / "sentence-transformers__all-MiniLM-L6-v2"
    sft_dir = DATA_DIR / "sft"

    evidence_paths = {
        "fdc": normalized_dir / "evidence_fdc.jsonl",
        "nih_ods": normalized_dir / "evidence_nih_ods.jsonl",
        "dsld": normalized_dir / "evidence_dsld.jsonl",
        "exrx": normalized_dir / "evidence_exrx.jsonl",
        "musclewiki": normalized_dir / "evidence_musclewiki.jsonl",
        "cdc": normalized_dir / "evidence_cdc.jsonl",
        "medlineplus": normalized_dir / "evidence_medlineplus.jsonl",
        "who": normalized_dir / "evidence_who.jsonl",
        "hhs": normalized_dir / "evidence_hhs.jsonl",
        "acsm": normalized_dir / "evidence_acsm.jsonl",
        "nia": normalized_dir / "evidence_nia.jsonl",
        "aha": normalized_dir / "evidence_aha.jsonl",
        "acog": normalized_dir / "evidence_acog.jsonl",
        "pubmed": normalized_dir / "evidence_pubmed.jsonl",
        "pmc": normalized_dir / "evidence_pmc.jsonl",
        "all": normalized_dir / "evidence_all.jsonl",
    }
    evidence_counts = {name: count_jsonl(path) for name, path in evidence_paths.items()}

    embedding_manifest = load_json(embeddings_dir / "manifest.json")
    validation_report = load_json(sft_dir / "grounded_examples_validation.json")
    curation_report = load_json(sft_dir / "grounded_examples_curation_report.json")

    lines = [
        "QwenF1 Project Summary",
        f"root={ROOT}",
        "",
        "[Corpus]",
        f"normalized_total={evidence_counts['all']}",
        f"cleaned_total={count_jsonl(ingestion_dir / 'evidence_cleaned.jsonl')}",
        f"chunk_total={count_jsonl(ingestion_dir / 'evidence_chunks.jsonl')}",
        "",
        "[Sources]",
    ]

    for name in [
        "fdc",
        "nih_ods",
        "dsld",
        "exrx",
        "musclewiki",
        "pubmed",
        "pmc",
        "cdc",
        "medlineplus",
        "who",
        "hhs",
        "acsm",
        "nia",
        "aha",
        "acog",
    ]:
        lines.append(f"{name}={evidence_counts[name]}")

    lines.extend(
        [
            "",
            "[Embeddings]",
            f"model={embedding_manifest.get('model', 'missing')}",
            f"vectors={embedding_manifest.get('records', 0)}",
            f"dimensions={embedding_manifest.get('dimensions', 0)}",
            f"manifest={fmt_path(embeddings_dir / 'manifest.json')}",
            "",
            "[Grounded Generation]",
            f"seed_count={len(load_json(ROOT / 'configs' / 'grounded_generation_seeds.json').get('seeds', []))}",
            f"prompt_count={count_jsonl(sft_dir / 'grounded_generation_inputs.jsonl')}",
            f"generated_count={count_jsonl(sft_dir / 'grounded_examples.jsonl')}",
            f"valid_count={validation_report.get('valid_examples', 0)}",
            f"invalid_count={validation_report.get('invalid_examples', 0)}",
            f"failed_generation_count={count_jsonl(sft_dir / 'grounded_generation_failures.jsonl')}",
            f"train_ready_count={curation_report.get('train_ready_examples', 0)}",
            f"rejected_after_curation={curation_report.get('rejected_examples', 0)}",
            f"validation_report={fmt_path(sft_dir / 'grounded_examples_validation.json')}",
            f"curation_report={fmt_path(sft_dir / 'grounded_examples_curation_report.json')}",
            f"failure_log={fmt_path(sft_dir / 'grounded_generation_failures.jsonl')}",
            "",
            "[Key Files]",
            f"project_context={fmt_path(ROOT / 'PROJECT_CONTEXT.md')}",
            f"readme={fmt_path(ROOT / 'README.md')}",
            f"dataset_doc={fmt_path(ROOT / 'docs' / 'dataset.md')}",
            f"methodology_doc={fmt_path(ROOT / 'docs' / 'methodology.md')}",
            f"evaluation_doc={fmt_path(ROOT / 'docs' / 'evaluation_plan.md')}",
        ]
    )

    print("\n".join(lines))


if __name__ == "__main__":
    main()
