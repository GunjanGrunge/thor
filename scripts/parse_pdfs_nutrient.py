"""Parse PDFs using the Nutrient DWS (Document Web Services) API with rolling
key rotation across all available NUTRIENT_* keys.

Reads raw PDF sources in the same sidecar-JSON format used by
scrape_nasm_pdfs.py and outputs parsed JSON artifacts that are compatible with
normalize_evidence_corpus.normalize_parsed_pdf_source().

Output layout:
    data/parsed/nutrient/<source>/<slug>.json

Each output file has the schema:
    {
      "parsed_at": "<iso>",
      "parser": {"provider": "nutrient", "key_slot": N},
      "source_document": {<sidecar metadata>},
      "documents": [{"index": 0, "text": "<full extracted text>", "metadata": {}}]
    }

Nutrient DWS API reference:
    POST https://api.nutrient.io/build
    Authorization: Bearer <key>
    Content-Type: multipart/form-data
    Body:
        instructions  (JSON string): {"parts": [{"file": "document"}],
                                      "output": {"type": "json-content"}}
        document      (file):        <PDF binary>

Usage:
    python scripts/parse_pdfs_nutrient.py --source nasm [--limit 5] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from common import DATA_DIR, ROOT, ensure_dir, utc_now_iso


RAW_DIR = DATA_DIR / "raw"
PARSED_DIR = DATA_DIR / "parsed" / "nutrient"

NUTRIENT_API_URL = "https://api.nutrient.io/build"

KEY_ENV_PREFIXES = (
    "NUTRIENT_API_KEY",
    "NUTRIENT_ACCESSIBILITY_KEY",
)

INSTRUCTIONS_JSON_CONTENT = json.dumps(
    {
        "parts": [{"file": "document"}],
        "output": {
            "type": "json-content",
            "plainText": True,
            "structuredText": True,
        },
    }
)


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip("'").strip('"')
        if name and name not in os.environ:
            os.environ[name] = value


def load_nutrient_keys() -> list[str]:
    load_dotenv(ROOT / ".env")
    keys: list[str] = []
    seen: set[str] = set()
    candidate_names = sorted(
        name
        for name in os.environ
        if any(name == prefix or name.startswith(f"{prefix}_") for prefix in KEY_ENV_PREFIXES)
    )
    for name in candidate_names:
        value = os.getenv(name, "").strip()
        if value and value.startswith("pdf_") and value not in seen:
            keys.append(value)
            seen.add(value)
    return keys


class KeyRotator:
    def __init__(self, keys: list[str], max_per_key: int) -> None:
        if not keys:
            raise ValueError("No Nutrient API keys found (expected NUTRIENT_API_KEY or NUTRIENT_ACCESSIBILITY_KEY_* in .env).")
        self._keys = keys
        self._max = max_per_key
        self._usage = [0] * len(keys)
        self._cursor = 0

    def next_key(self) -> tuple[str, int]:
        budget = len(self._keys) * self._max
        if sum(self._usage) >= budget:
            raise RuntimeError(f"All Nutrient key budgets exhausted ({self._max} requests × {len(self._keys)} keys).")
        for _ in range(len(self._keys)):
            slot = self._cursor % len(self._keys)
            self._cursor += 1
            if self._usage[slot] < self._max:
                self._usage[slot] += 1
                return self._keys[slot], slot + 1
        raise RuntimeError("No Nutrient key has remaining budget.")

    def usage_summary(self) -> list[dict[str, int]]:
        return [{"key_slot": i + 1, "requests_used": u} for i, u in enumerate(self._usage)]


# ---------------------------------------------------------------------------
# Nutrient API helpers
# ---------------------------------------------------------------------------

def extract_text_from_json_content(data: dict[str, Any]) -> str:
    """Pull text from Nutrient json-content API response.

    With plainText=true, each page has a top-level 'plainText' field.
    Falls back to textLines / structuredText spans if plainText is absent.
    """
    page_texts: list[str] = []
    for page in data.get("pages", []):
        # Preferred: plainText field (present when plainText=true in instructions)
        plain = (page.get("plainText") or "").strip()
        if plain:
            page_texts.append(plain)
            continue

        # Fallback 1: structuredText blocks
        lines: list[str] = []
        for block in page.get("structuredText", {}).get("paragraphs", []):
            for line in block.get("lines", []):
                text = " ".join(span.get("text", "") for span in line.get("spans", [])).strip()
                if text:
                    lines.append(text)

        # Fallback 2: textLines array
        if not lines:
            for text_line in page.get("textLines", []):
                content = text_line.get("contents", "").strip()
                if content:
                    lines.append(content)

        if lines:
            page_texts.append("\n".join(lines))

    return "\n\n".join(page_texts)


def parse_pdf_with_nutrient(
    pdf_path: Path,
    api_key: str,
    client: httpx.Client,
) -> str:
    """Call the Nutrient DWS API and return extracted text."""
    with open(pdf_path, "rb") as fh:
        pdf_bytes = fh.read()

    response = client.post(
        NUTRIENT_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        data={"instructions": INSTRUCTIONS_JSON_CONTENT},
        files={"document": (pdf_path.name, pdf_bytes, "application/pdf")},
        timeout=120.0,
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "json" in content_type:
        data = response.json()
        return extract_text_from_json_content(data)

    # Fallback: treat response body as plain text
    return response.text.strip()


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------

def discover_pdfs(source: str) -> list[dict[str, Any]]:
    source_dir = RAW_DIR / source
    if not source_dir.exists():
        raise FileNotFoundError(f"Raw source directory not found: {source_dir}")

    docs: list[dict[str, Any]] = []
    for sidecar in sorted(source_dir.glob("*.json")):
        if sidecar.name == "manifest.json":
            continue
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
        except Exception:
            continue
        pdf_field = next(
            (f for f in ("pdf_path", "file_path") if payload.get(f)),
            None,
        )
        if not pdf_field:
            continue
        pdf_path = sidecar.with_name(payload[pdf_field])
        if not pdf_path.exists():
            continue
        docs.append(
            {
                "sidecar": sidecar,
                "pdf_path": pdf_path,
                "metadata": payload,
            }
        )
    return docs


def output_path(source: str, pdf_path: Path) -> Path:
    stem = re.sub(r"[^a-zA-Z0-9_-]", "_", pdf_path.stem)
    return PARSED_DIR / source / f"{stem}.json"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Parse PDFs with Nutrient DWS API (rolling key rotation).")
    p.add_argument("--source", action="append", required=True, help="Raw source bucket name (e.g. nasm).")
    p.add_argument("--limit", type=int, default=0, help="Max PDFs to parse per source. 0 = no limit.")
    p.add_argument("--force", action="store_true", help="Re-parse PDFs that already have output files.")
    p.add_argument("--max-per-key", type=int, default=500, help="Max requests per key before rotating (default 500).")
    p.add_argument("--delay", type=float, default=0.5, help="Seconds between API calls (default 0.5).")
    return p.parse_args()


def main() -> None:
    # Inline import needed for output_path helper using re
    import re as _re
    global re
    re = _re

    args = parse_args()
    keys = load_nutrient_keys()
    print(f"Loaded {len(keys)} Nutrient key(s).")
    rotator = KeyRotator(keys, args.max_per_key)

    total_ok = total_skip = total_fail = 0

    with httpx.Client() as client:
        for source in args.source:
            print(f"\n=== Source: {source} ===")
            try:
                docs = discover_pdfs(source)
            except FileNotFoundError as exc:
                print(f"  {exc}")
                continue

            if args.limit:
                docs = docs[: args.limit]

            out_base = PARSED_DIR / source
            ensure_dir(out_base)

            for i, doc in enumerate(docs):
                pdf_path: Path = doc["pdf_path"]
                metadata: dict = doc["metadata"]
                out_file = output_path(source, pdf_path)

                if out_file.exists() and not args.force:
                    print(f"  [{i + 1}/{len(docs)}] skip (parsed): {pdf_path.name}")
                    total_skip += 1
                    continue

                print(f"  [{i + 1}/{len(docs)}] parsing: {pdf_path.name}")
                try:
                    api_key, key_slot = rotator.next_key()
                    text = parse_pdf_with_nutrient(pdf_path, api_key, client)
                except Exception as exc:
                    print(f"    error: {exc}")
                    total_fail += 1
                    continue

                result = {
                    "parsed_at": utc_now_iso(),
                    "parser": {
                        "provider": "nutrient",
                        "key_slot": key_slot,
                    },
                    "source_document": {
                        "source": source,
                        "title": metadata.get("title") or pdf_path.stem,
                        "url": metadata.get("url", ""),
                        "document_path": str(pdf_path),
                        "sidecar_path": str(doc["sidecar"]),
                        "metadata": {k: v for k, v in metadata.items() if k not in {"title", "url", "pdf_path"}},
                    },
                    "documents": [
                        {
                            "index": 0,
                            "text": text,
                            "metadata": {},
                            "doc_id": None,
                        }
                    ],
                }
                out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"    -> {len(text)} chars extracted (key slot {key_slot})")
                total_ok += 1

                if i < len(docs) - 1:
                    time.sleep(args.delay)

    print(f"\nKey usage: {rotator.usage_summary()}")
    print(f"Total: {total_ok} parsed, {total_skip} skipped, {total_fail} failed")


if __name__ == "__main__":
    main()
