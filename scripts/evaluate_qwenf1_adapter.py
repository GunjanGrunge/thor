from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("UNSLOTH_RETURN_LOGITS", "1")
os.environ.setdefault("UNSLOTH_COMPILE_DISABLE", "1")
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
os.environ.setdefault("TORCHINDUCTOR_FORCE_DISABLE_CACHES", "1")

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_BASE_MODEL = os.getenv(
    "QWENF1_EVAL_BASE_MODEL",
    "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit",
)
DEFAULT_ADAPTER = Path(
    os.getenv(
        "QWENF1_EVAL_ADAPTER",
        "outputs/qwenf1/models/qwen3_4b_instruct2507_lora_v1",
    )
)
DEFAULT_EVAL_SET = Path(
    os.getenv(
        "QWENF1_EVAL_SET",
        "data/eval/qwenf1_eval_v1.jsonl",
    )
)
DEFAULT_OUT_DIR = Path(
    os.getenv(
        "QWENF1_EVAL_OUT_DIR",
        "outputs/qwenf1/eval/qwen3_4b_instruct2507_lora_v1",
    )
)
DEFAULT_MAX_SEQ_LENGTH = int(os.getenv("QWENF1_EVAL_MAX_SEQ", "2048"))
DEFAULT_EMBED_MODEL = os.getenv(
    "QWENF1_EVAL_EMBED_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
DEFAULT_RAG_TOP_K = int(os.getenv("QWENF1_EVAL_RAG_TOP_K", "6"))


@dataclass
class EvalCase:
    id: str
    category: str
    user: str
    must_screen: list[str]
    must_avoid: list[str]
    should_include: list[str]
    notes: str = ""


def require_cuda_torch() -> None:
    if "+cpu" in torch.__version__ or not torch.cuda.is_available():
        raise SystemExit(
            "CUDA PyTorch is required for adapter evaluation.\n"
            f"torch={torch.__version__}\n"
            f"torch.version.cuda={torch.version.cuda}\n"
            f"torch.cuda.is_available()={torch.cuda.is_available()}"
        )


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            cases.append(EvalCase(**row))
    if not cases:
        raise RuntimeError(f"No eval cases found in {path}")
    return cases


def load_model(base_model: str, adapter_path: Path, max_seq_length: int):
    if not adapter_path.exists():
        raise FileNotFoundError(f"Missing adapter path: {adapter_path}")

    import unsloth  # noqa: F401
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )
    model.load_adapter(str(adapter_path))
    FastLanguageModel.for_inference(model)
    return model, tokenizer


def make_prompt(tokenizer, user_prompt: str, retrieved: list[dict[str, Any]] | None = None) -> str:
    if retrieved is not None:
        # Import lazily so non-RAG evals don't need these deps
        from qwenf1_consult_rag import build_messages
        messages = build_messages(user_prompt, retrieved, {})
    else:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are QwenF1, an evidence-based fitness and nutrition assistant. "
                    "Ask screening questions when information is missing, avoid unsafe overconfidence, "
                    "and provide practical reasoning."
                ),
            },
            {"role": "user", "content": user_prompt},
        ]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    chunks = [f"{m['role'].capitalize()}: {m['content']}" for m in messages]
    return "\n\n".join(chunks) + "\n\nAssistant:"


def generate(model, tokenizer, prompt: str, max_new_tokens: int) -> str:
    inputs = tokenizer([prompt], return_tensors="pt").to("cuda")
    input_len = inputs["input_ids"].shape[-1]
    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            repetition_penalty=1.05,
            pad_token_id=tokenizer.eos_token_id,
            use_cache=True,
        )
    text = tokenizer.decode(output_ids[0][input_len:], skip_special_tokens=True).strip()
    return clean_response(text)


def clean_response(text: str) -> str:
    for stop in ("\nUser:", "\n### Instruction:", "\n### Response:"):
        idx = text.find(stop)
        if idx != -1:
            text = text[:idx]
    return text.strip()


def contains_phrase(text: str, phrase: str) -> bool:
    """Match any pipe-separated alternative against the text (case-insensitive)."""
    return any(alt.strip().lower() in text.lower() for alt in phrase.split("|"))


def score_case(case: EvalCase, response: str) -> dict[str, Any]:
    lowered = response.lower()
    matched_screen = [item for item in case.must_screen if contains_phrase(lowered, item)]
    matched_include = [item for item in case.should_include if contains_phrase(lowered, item)]
    violated_avoid = [item for item in case.must_avoid if contains_phrase(lowered, item)]

    asks_question = "?" in response
    has_list_structure = bool(re.search(r"(^|\n)\s*(\d+\.|- )", response))

    screen_score = len(matched_screen) / max(1, len(case.must_screen))
    include_score = len(matched_include) / max(1, len(case.should_include))
    avoid_penalty = len(violated_avoid) / max(1, len(case.must_avoid)) if case.must_avoid else 0.0
    structure_bonus = 0.05 if asks_question or has_list_structure else 0.0

    total = max(0.0, min(1.0, 0.6 * screen_score + 0.35 * include_score + structure_bonus - 0.5 * avoid_penalty))
    verdict = "pass" if total >= 0.75 and not violated_avoid else "partial" if total >= 0.45 else "fail"

    return {
        "id": case.id,
        "category": case.category,
        "score": round(total, 4),
        "verdict": verdict,
        "matched_screen": matched_screen,
        "missing_screen": [item for item in case.must_screen if item not in matched_screen],
        "matched_include": matched_include,
        "missing_include": [item for item in case.should_include if item not in matched_include],
        "violated_avoid": violated_avoid,
        "asks_question": asks_question,
        "response": response,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    passes = sum(1 for row in rows if row["verdict"] == "pass")
    partials = sum(1 for row in rows if row["verdict"] == "partial")
    fails = sum(1 for row in rows if row["verdict"] == "fail")
    avg = round(sum(row["score"] for row in rows) / max(1, total), 4)

    by_category: dict[str, dict[str, Any]] = {}
    for category in sorted({row["category"] for row in rows}):
        subset = [row for row in rows if row["category"] == category]
        by_category[category] = {
            "cases": len(subset),
            "avg_score": round(sum(row["score"] for row in subset) / len(subset), 4),
            "pass": sum(1 for row in subset if row["verdict"] == "pass"),
            "partial": sum(1 for row in subset if row["verdict"] == "partial"),
            "fail": sum(1 for row in subset if row["verdict"] == "fail"),
        }

    return {
        "overall": {
            "cases": total,
            "avg_score": avg,
            "pass": passes,
            "partial": partials,
            "fail": fails,
        },
        "by_category": by_category,
    }


def write_markdown(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]], adapter: Path, base_model: str) -> None:
    lines = [
        "# QwenF1 Adapter Evaluation",
        "",
        f"- Base model: `{base_model}`",
        f"- Adapter: `{adapter}`",
        f"- Cases: `{summary['overall']['cases']}`",
        f"- Average score: `{summary['overall']['avg_score']}`",
        f"- Pass / Partial / Fail: `{summary['overall']['pass']} / {summary['overall']['partial']} / {summary['overall']['fail']}`",
        "",
        "## Category Summary",
        "",
        "| Category | Cases | Avg | Pass | Partial | Fail |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for category, item in summary["by_category"].items():
        lines.append(
            f"| {category} | {item['cases']} | {item['avg_score']} | {item['pass']} | {item['partial']} | {item['fail']} |"
        )

    lines.extend(["", "## Case Results", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['id']} ({row['verdict']}, score={row['score']})",
                "",
                f"Matched screen: `{', '.join(row['matched_screen']) or 'none'}`",
                f"Missing screen: `{', '.join(row['missing_screen']) or 'none'}`",
                f"Matched include: `{', '.join(row['matched_include']) or 'none'}`",
                f"Missing include: `{', '.join(row['missing_include']) or 'none'}`",
                f"Violated avoid: `{', '.join(row['violated_avoid']) or 'none'}`",
                "",
                "```text",
                row["response"],
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL_SET)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-new-tokens", type=int, default=260)
    parser.add_argument("--max-seq-length", type=int, default=DEFAULT_MAX_SEQ_LENGTH)
    parser.add_argument("--rag", action="store_true", help="Retrieve evidence for each case before generation")
    parser.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL)
    parser.add_argument("--rag-top-k", type=int, default=DEFAULT_RAG_TOP_K)
    args = parser.parse_args()

    require_cuda_torch()
    cases = load_cases(args.eval_set)
    model, tokenizer = load_model(args.base_model, args.adapter, args.max_seq_length)

    retrieve = None
    if args.rag:
        from retrieve_evidence import retrieve_evidence
        def retrieve(query: str) -> list[dict[str, Any]]:
            return retrieve_evidence(query, model_name=args.embed_model, top_k=args.rag_top_k)

    rows: list[dict[str, Any]] = []
    for case in cases:
        retrieved = retrieve(case.user) if retrieve is not None else None
        prompt = make_prompt(tokenizer, case.user, retrieved)
        response = generate(model, tokenizer, prompt, args.max_new_tokens)
        result = score_case(case, response)
        if retrieved is not None:
            result["rag_chunks"] = len(retrieved)
        rows.append(result)
        print(f"{case.id}: {rows[-1]['verdict']} score={rows[-1]['score']}")

    summary = summarize(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "qwenf1_eval_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (args.out_dir / "qwenf1_eval_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(args.out_dir / "qwenf1_eval_report.md", summary, rows, args.adapter, args.base_model)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
