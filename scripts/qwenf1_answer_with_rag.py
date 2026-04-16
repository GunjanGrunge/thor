from __future__ import annotations

import argparse
import json
import os
import sys
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

from qwenf1_consult_rag import build_messages, load_profile
from retrieve_evidence import retrieve_evidence


DEFAULT_BASE_MODEL = os.getenv(
    "QWENF1_RAG_BASE_MODEL",
    "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit",
)
DEFAULT_ADAPTER = Path(
    os.getenv(
        "QWENF1_RAG_ADAPTER",
        "outputs/qwenf1/models/qwen3_4b_instruct2507_lora_v1",
    )
)
DEFAULT_EMBED_MODEL = os.getenv(
    "QWENF1_RAG_EMBED_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
DEFAULT_MAX_SEQ_LENGTH = int(os.getenv("QWENF1_RAG_MAX_SEQ", "2048"))


def require_cuda_torch() -> None:
    if "+cpu" in torch.__version__ or not torch.cuda.is_available():
        raise SystemExit(
            "CUDA PyTorch is required for QwenF1 RAG inference.\n"
            f"torch={torch.__version__}\n"
            f"torch.version.cuda={torch.version.cuda}\n"
            f"torch.cuda.is_available()={torch.cuda.is_available()}"
        )


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


def make_prompt(tokenizer, messages: list[dict[str, str]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    chunks = []
    for msg in messages:
        chunks.append(f"{msg['role'].capitalize()}: {msg['content']}")
    chunks.append("Assistant:")
    return "\n\n".join(chunks)


def clean_response(text: str) -> str:
    for stop in ("\nUser:", "\n### Instruction:", "\n### Response:"):
        idx = text.find(stop)
        if idx != -1:
            text = text[:idx]
    return text.strip()


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


def load_payload(
    payload_json: Path | None,
    query: str | None,
    profile_json: Path | None,
    embed_model: str,
    top_k: int,
) -> dict[str, Any]:
    if payload_json is not None:
        return json.loads(payload_json.read_text(encoding="utf-8"))
    if not query:
        raise ValueError("Provide either --payload-json or --query.")

    profile = load_profile(profile_json)
    retrieved = retrieve_evidence(query, model_name=embed_model, top_k=top_k)
    return {
        "query": query,
        "profile": profile,
        "retrieved_evidence": retrieved,
        "messages": build_messages(query, retrieved, profile),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-json", type=Path, default=None)
    parser.add_argument("--query", default=None)
    parser.add_argument("--profile-json", type=Path, default=None)
    parser.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--max-new-tokens", type=int, default=360)
    parser.add_argument("--max-seq-length", type=int, default=DEFAULT_MAX_SEQ_LENGTH)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    require_cuda_torch()
    payload = load_payload(args.payload_json, args.query, args.profile_json, args.embed_model, args.top_k)
    model, tokenizer = load_model(args.base_model, args.adapter, args.max_seq_length)
    prompt = make_prompt(tokenizer, payload["messages"])
    answer = generate(model, tokenizer, prompt, args.max_new_tokens)

    result = {
        "query": payload.get("query"),
        "profile": payload.get("profile", {}),
        "retrieved_evidence": payload.get("retrieved_evidence", []),
        "messages": payload["messages"],
        "answer": answer,
        "adapter": str(args.adapter),
        "base_model": args.base_model,
    }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
