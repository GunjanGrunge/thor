from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from retrieve_evidence import retrieve_evidence


SYSTEM_PROMPT = (
    "You are QwenF1, an evidence-based fitness and nutrition consultation assistant. "
    "Your job is to ask the right screening questions, adapt guidance to injuries, disease, goals, "
    "preferences, and equipment constraints, and avoid unsupported certainty. "
    "Use the retrieved evidence as support for reasoning. If key information is missing, ask for it "
    "before finalizing a plan. You may give a conservative provisional direction when appropriate."
)


def sanitize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def truncate_text(text: str, max_chars: int = 700) -> str:
    text = sanitize_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def load_profile(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def profile_block(profile: dict[str, Any]) -> str:
    if not profile:
        return "No structured user profile provided."
    lines = []
    for key, value in profile.items():
        if value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            value_text = ", ".join(str(item) for item in value)
        else:
            value_text = str(value)
        lines.append(f"- {key}: {sanitize_text(value_text)}")
    return "\n".join(lines) if lines else "No structured user profile provided."


def evidence_block(items: list[dict[str, Any]]) -> str:
    lines = []
    for idx, item in enumerate(items, start=1):
        first_url = (item.get("grounding_urls") or [""])[0]
        lines.extend(
            [
                f"[{idx}] source={item.get('source')}",
                f"title={sanitize_text(str(item.get('title', '')))}",
                f"url={first_url}",
                f"text={truncate_text(str(item.get('text', '')))}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def build_messages(user_query: str, retrieved: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, str]]:
    user_prompt = "\n".join(
        [
            f"User query: {sanitize_text(user_query)}",
            "",
            "Known profile:",
            profile_block(profile),
            "",
            "Retrieved evidence:",
            evidence_block(retrieved),
            "",
            "Instructions:",
            "- Ask targeted screening questions when important details are missing.",
            "- Explain briefly why those questions matter.",
            "- Give a conservative provisional direction if it is safe to do so.",
            "- Keep the answer in plain prose, not YAML or schema output.",
            "- Refer to evidence using inline markers like [1], [2] only when making substantive claims.",
            "- Do not invent studies or source claims beyond the retrieved evidence.",
        ]
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--profile-json", type=Path, default=None)
    parser.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    profile = load_profile(args.profile_json)
    retrieved = retrieve_evidence(args.query, model_name=args.embed_model, top_k=args.top_k)
    payload = {
        "system_prompt": SYSTEM_PROMPT,
        "query": args.query,
        "profile": profile,
        "retrieved_evidence": retrieved,
        "messages": build_messages(args.query, retrieved, profile),
    }

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
