from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import jsonlines
import numpy as np
import requests
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "configs"
DATA_DIR = ROOT / "data"
EMBED_DIR = DATA_DIR / "embeddings"
SFT_DIR = DATA_DIR / "sft"


def sanitize_model_name(model_name: str) -> str:
    return model_name.replace("/", "__")


def maybe_set_windows_hf_cache() -> None:
    windows_cache = "/mnt/c/Users/Bot/.cache/huggingface"
    if Path(windows_cache).exists() and "HF_HOME" not in os.environ:
        os.environ["HF_HOME"] = windows_cache


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_text(text: str) -> str:
    # Remove control characters that can break downstream JSON payloads.
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text or "")
    return re.sub(r"[ \t]+", " ", cleaned).strip()


def truncate_text(text: str, max_chars: int = 1400) -> str:
    text = sanitize_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def load_metadata(path: Path) -> list[dict[str, Any]]:
    with jsonlines.open(path, mode="r") as reader:
        return list(reader)


def retrieve(
    query: str,
    embed_model_name: str,
    top_k: int,
) -> list[dict[str, Any]]:
    maybe_set_windows_hf_cache()
    base_dir = EMBED_DIR / sanitize_model_name(embed_model_name)
    metadata = load_metadata(base_dir / "metadata.jsonl")
    embeddings = np.load(base_dir / "embeddings.npy", mmap_mode="r")

    embed_model = SentenceTransformer(embed_model_name)
    query_embedding = embed_model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)[0]

    scores = embeddings @ query_embedding
    top_indices = np.argsort(scores)[-top_k:][::-1]

    results = []
    for idx in top_indices.tolist():
        item = metadata[idx]
        results.append(
            {
                "score": float(scores[idx]),
                "chunk_id": item.get("chunk_id"),
                "record_id": item.get("record_id"),
                "source": item.get("source"),
                "domain": item.get("domain"),
                "record_type": item.get("record_type"),
                "title": item.get("title"),
                "text": item.get("text"),
                "grounding_urls": item.get("grounding_urls", []),
            }
        )
    return results


def build_prompt(seed: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    evidence_block = []
    for idx, item in enumerate(evidence, start=1):
        evidence_block.append(
            "\n".join(
                [
                    f"[{idx}] source={item['source']}",
                    f"title={sanitize_text(item['title'])}",
                    f"url={(item.get('grounding_urls') or [''])[0]}",
                    f"text={truncate_text(item['text'])}",
                ]
            )
        )

    prompt = f"""
You are generating one high-quality grounded training example for an evidence-based exercise physiology and sports nutrition assistant.

Return valid JSON only.

Required JSON schema:
{{
  "assistant": "string",
  "screening_points": ["string"],
  "evidence_used": [
    {{
      "citation_id": integer,
      "source": "string",
      "title": "string",
      "url": "string"
    }}
  ]
}}

Rules:
- The assistant must be cautious, specific, and evidence-grounded.
- The assistant must not act like a physician, but it must be screening-aware.
- The assistant must ask for missing information before finalizing a full plan when necessary.
- The assistant should explicitly mention why the missing information matters.
- The assistant may provide a provisional safe starting direction, but should not overprescribe when screening details are missing.
- The assistant must sound like a real coach-clinician hybrid talking to a person, not like a database, form, YAML block, rubric, or extraction schema.
- The assistant must be plain prose in short paragraphs or bullets only when useful.
- Do not output field labels such as `title:`, `question_order:`, `screening_questions:`, `section:`, `reference:`, `source:`, or placeholder values like `:section_1`.
- Do not answer with generic filler such as `How can I assist you?`.
- Lead with a brief acknowledgement of the goal and risk context, then ask the most important missing screening questions, then give a conservative provisional next step.
- The assistant should use inline citation markers like [1], [2] inside the assistant answer when making substantive claims.
- Use only the evidence provided below. Do not invent studies or sources.
- Prefer exercise physiology, safety, condition-aware adaptation, and sports nutrition reasoning over generic fitness talk.
- Do not cite evidence that is clearly mismatched to the user population or scenario. For example, avoid pediatric evidence for adult queries unless it is explicitly relevant.
- Keep citations selective. Use only the most relevant evidence items.
- Use at most 3 citations in the assistant answer.
- `evidence_used` must contain only the citations that appear inline in the assistant answer.
- Every inline citation number must appear exactly once in `evidence_used`.
- Do not include uncited evidence in `evidence_used`.
- `screening_points` must contain 3 to 6 concrete items and must not contain null, empty strings, or duplicates.
- If the user has a condition, do not recommend a named exercise or machine unless the evidence directly supports that recommendation for the scenario.
- Before returning JSON, self-check that the assistant text, `screening_points`, and `evidence_used` are mutually consistent.
- Before returning JSON, self-check that the assistant answer would pass this test:
  1) it asks targeted questions,
  2) it gives a safe provisional direction,
  3) it does not look like structured metadata or template output.

Seed ID: {seed["id"]}
Domain: {seed["domain"]}
User query: {seed["user_query"]}
Notes: {seed["notes"]}

Evidence:
{chr(10).join(evidence_block)}
""".strip()
    return sanitize_text(prompt).replace("\\n", "\n")


def ollama_generate(model: str, prompt: str, host: str) -> dict[str, Any]:
    response = requests.post(
        f"{host}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        },
        timeout=300,
    )
    response.raise_for_status()
    payload = response.json()
    return json.loads(payload["response"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-config", default=str(CONFIG_DIR / "grounded_generation_seeds.json"))
    parser.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--gen-model", default="qwen3:8b")
    parser.add_argument("--ollama-host", default=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"))
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", default=str(SFT_DIR / "grounded_examples.jsonl"))
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--prompt-output", default=str(SFT_DIR / "grounded_generation_inputs.jsonl"))
    args = parser.parse_args()

    seeds = json.loads(Path(args.seed_config).read_text(encoding="utf-8"))["seeds"]
    if args.limit is not None:
        seeds = seeds[: args.limit]

    ensure_dir(Path(args.output).parent)

    outputs = []
    prompt_records = []
    for seed in seeds:
        evidence = retrieve(seed["user_query"], args.embed_model, args.top_k)
        prompt = build_prompt(seed, evidence)
        prompt_record = {
            "id": seed["id"],
            "domain": seed["domain"],
            "seed": seed,
            "prompt": prompt,
            "retrieved_evidence": evidence,
            "generator_model": args.gen_model,
            "embedding_model": args.embed_model,
        }
        prompt_records.append(prompt_record)
        if args.prepare_only:
            continue
        generated = ollama_generate(args.gen_model, prompt, args.ollama_host)
        outputs.append(
            {
                "id": seed["id"],
                "domain": seed["domain"],
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a fitness and nutrition assistant grounded in evidence-based exercise physiology and sports nutrition.",
                    },
                    {"role": "user", "content": seed["user_query"]},
                    {"role": "assistant", "content": generated["assistant"]},
                ],
                "screening_points": generated.get("screening_points", []),
                "evidence_used": generated.get("evidence_used", []),
                "retrieved_evidence": evidence,
                "generator_model": args.gen_model,
                "embedding_model": args.embed_model,
            }
        )

    with jsonlines.open(args.prompt_output, mode="w") as writer:
        writer.write_all(prompt_records)

    if args.prepare_only:
        print(json.dumps({"prompt_output": args.prompt_output, "examples": len(prompt_records)}, indent=2))
        return

    with jsonlines.open(args.output, mode="w") as writer:
        writer.write_all(outputs)

    print(json.dumps({"output": args.output, "examples": len(outputs), "prompt_output": args.prompt_output}, indent=2))


if __name__ == "__main__":
    main()
