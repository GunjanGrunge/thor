from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonlines

from common import DATA_DIR, ROOT, ensure_dir, utc_now_iso

try:
    from llama_cloud_services import LlamaParse
except ImportError:  # pragma: no cover - handled at runtime
    LlamaParse = None  # type: ignore[assignment]


RAW_DIR = DATA_DIR / "raw"
PARSED_DIR = DATA_DIR / "parsed" / "llamaparse"
SUPPORTED_EXTENSIONS = {".html", ".htm", ".xml", ".gif", ".pdf", ".doc", ".docx", ".txt"}
BLOCKED_TITLE_FRAGMENTS = {
    "page forbidden",
    "page not found",
}
API_KEY_PREFIXES = (
    "LLAMA_CLOUD_API_KEY",
    "NUTRIENT_ACCESSIBILITY_KEY",
)


@dataclass
class SourceDocument:
    source: str
    title: str
    url: str
    document_path: Path
    sidecar_path: Path | None
    metadata: dict[str, Any]


class KeyRotator:
    def __init__(self, keys: list[str], max_requests_per_key: int) -> None:
        if not keys:
            raise ValueError("No Llama Cloud API keys were found in the environment.")
        self._keys = keys
        self._max_requests_per_key = max_requests_per_key
        self._cursor = 0
        self._usage = [0 for _ in keys]

    def next_key(self) -> tuple[str, int]:
        total_budget = len(self._keys) * self._max_requests_per_key
        if sum(self._usage) >= total_budget:
            raise RuntimeError(
                f"Per-run key budget exhausted ({self._max_requests_per_key} requests across {len(self._keys)} keys)."
            )

        for _ in range(len(self._keys)):
            slot = self._cursor % len(self._keys)
            self._cursor += 1
            if self._usage[slot] < self._max_requests_per_key:
                # Key is not exhausted
                return self._keys[slot], slot + 1
        raise RuntimeError("No key had remaining request budget.")

    def increment_usage(self, slot: int) -> None:
        self._usage[slot - 1] += 1

    def mark_bad_key(self, slot: int) -> None:
        """Mark a key as exhausted (max out its usage) if it returns an auth error."""
        self._usage[slot - 1] = self._max_requests_per_key

    def usage_summary(self) -> list[dict[str, int]]:
        return [
            {"key_slot": idx + 1, "requests_usage": used}
            for idx, used in enumerate(self._usage)
        ]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_sidecar_docs(source: str) -> list[SourceDocument]:
    source_dir = RAW_DIR / source
    if not source_dir.exists():
        raise FileNotFoundError(f"Raw source directory does not exist: {source_dir}")

    documents: list[SourceDocument] = []
    for sidecar in sorted(source_dir.glob("*.json")):
        if sidecar.name == "manifest.json":
            continue
        payload = load_json(sidecar)
        doc_field = next(
            (field for field in ("html_path", "xml_path", "pdf_path", "file_path") if payload.get(field)),
            None,
        )
        if not doc_field:
            continue
        url = payload.get("url") or ""
        if "${" in url or "}" in url:
            continue
        document_path = sidecar.with_name(payload[doc_field])
        if not document_path.exists():
            continue
        if document_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        title = payload.get("title") or sidecar.stem
        if any(fragment in title.lower() for fragment in BLOCKED_TITLE_FRAGMENTS):
            continue
        documents.append(
            SourceDocument(
                source=source,
                title=title,
                url=url,
                document_path=document_path,
                sidecar_path=sidecar,
                metadata={k: v for k, v in payload.items() if k not in {"title", "url", doc_field}},
            )
        )
    return documents


def load_api_keys() -> list[str]:
    load_dotenv(ROOT / ".env")
    keys: list[str] = []
    seen: set[str] = set()
    candidate_names = sorted(
        name
        for name in os.environ
        if any(name == prefix or name.startswith(f"{prefix}_") for prefix in API_KEY_PREFIXES)
    )
    for name in candidate_names:
        value = os.getenv(name, "").strip()
        if value and value not in seen:
            keys.append(value)
            seen.add(value)
    return keys


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


def sanitize_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in name)


def document_output_path(base_dir: Path, source: str, document_path: Path) -> Path:
    return base_dir / source / f"{sanitize_name(document_path.stem)}.json"


def build_parser(api_key: str, args: argparse.Namespace) -> Any:
    if LlamaParse is None:
        raise RuntimeError(
            "llama-cloud-services is not installed. Install it before running this parser."
        )
    return LlamaParse(
        api_key=api_key,
        result_type=args.result_type,
        num_workers=args.num_workers,
        verbose=args.verbose,
    )


def serialize_documents(parsed_docs: list[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for idx, doc in enumerate(parsed_docs):
        serialized.append(
            {
                "index": idx,
                "text": getattr(doc, "text", ""),
                "metadata": getattr(doc, "metadata", {}) or {},
                "doc_id": getattr(doc, "doc_id", None),
            }
        )
    return serialized


def parse_one(item: SourceDocument, api_key: str, key_slot: int, args: argparse.Namespace) -> dict[str, Any]:
    parser = build_parser(api_key, args)
    parsed_docs = parser.load_data(str(item.document_path))
    if not parsed_docs:
        raise RuntimeError(f"LlamaParse returned no documents for {item.document_path}")
    now = utc_now_iso()
    return {
        "parsed_at": now,
        "parser": {
            "provider": "llamaparse",
            "result_type": args.result_type,
            "num_workers": args.num_workers,
            "key_slot": key_slot,
        },
        "source_document": {
            "source": item.source,
            "title": item.title,
            "url": item.url,
            "document_path": str(item.document_path),
            "sidecar_path": str(item.sidecar_path) if item.sidecar_path else None,
            "metadata": item.metadata,
        },
        "documents": serialize_documents(parsed_docs),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse raw corpus documents with LlamaParse and rotate API keys.")
    parser.add_argument("--source", action="append", required=True, help="Raw source bucket to parse, e.g. exrx, nih_ods, pmc.")
    parser.add_argument(
        "--match",
        action="append",
        default=[],
        help="Optional case-insensitive substring filter on document filename or title. Repeat for multiple targets.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional limit per source. 0 means no limit.")
    parser.add_argument("--offset", type=int, default=0, help="Skip the first N discovered documents per source.")
    parser.add_argument("--resume-from-unparsed", action="store_true", help="Ignore manual offset semantics and start from the next document that is neither already parsed nor a known error.")
    parser.add_argument("--result-type", default="markdown", choices=["markdown", "text"], help="LlamaParse output format.")
    parser.add_argument("--num-workers", type=int, default=1, help="Parser worker count passed to LlamaParse.")
    parser.add_argument("--max-requests-per-key", type=int, default=2000, help="Per-run request budget for each key.")
    parser.add_argument("--force", action="store_true", help="Re-parse files even if an output JSON already exists.")
    parser.add_argument("--retry-failed", action="store_true", help="Retry documents that were previously recorded as errors.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose parser logging.")
    parser.add_argument("--output-dir", default=str(PARSED_DIR), help="Directory where parsed JSON artifacts are written.")
    return parser.parse_args()


def load_failed_documents(manifest_path: Path) -> set[str]:
    failed: set[str] = set()
    if not manifest_path.exists():
        return failed
    with jsonlines.open(manifest_path, mode="r") as reader:
        for row in reader:
            if not isinstance(row, dict):
                continue
            document_path = row.get("document_path")
            status = row.get("status")
            if not document_path:
                continue
            if status == "error":
                failed.add(document_path)
            elif status in {"parsed", "skipped_existing"} and document_path in failed:
                failed.discard(document_path)
    return failed


def select_documents(
    discovered: list[SourceDocument],
    output_dir: Path,
    source: str,
    known_failed: set[str],
    args: argparse.Namespace,
) -> list[SourceDocument]:
    if args.match:
        needles = [needle.lower() for needle in args.match]
        discovered = [
            item
            for item in discovered
            if any(
                needle in haystack
                for needle in needles
                for haystack in (item.document_path.name.lower(), item.title.lower())
            )
        ]

    if not args.resume_from_unparsed:
        selected = discovered[args.offset :]
        if args.limit > 0:
            selected = selected[: args.limit]
        return selected

    selected: list[SourceDocument] = []
    for item in discovered:
        out_path = document_output_path(output_dir, source, item.document_path)
        if out_path.exists():
            continue
        if str(item.document_path) in known_failed and not args.retry_failed and not args.force:
            continue
        selected.append(item)
        if args.limit > 0 and len(selected) >= args.limit:
            break
    return selected


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    keys = load_api_keys()
    rotator = KeyRotator(keys=keys, max_requests_per_key=args.max_requests_per_key)

    manifest_path = output_dir / "manifest.jsonl"
    retry_queue_path = output_dir / "retry_queue.jsonl"
    run_summary: list[dict[str, Any]] = []
    known_failed = load_failed_documents(manifest_path)

    with jsonlines.open(manifest_path, mode="a") as manifest:
        retry_queue = jsonlines.open(retry_queue_path, mode="a")
        for source in args.source:
            discovered = discover_sidecar_docs(source)
            selected = select_documents(
                discovered=discovered,
                output_dir=output_dir,
                source=source,
                known_failed=known_failed,
                args=args,
            )

            for item in selected:
                out_path = document_output_path(output_dir, source, item.document_path)
                ensure_dir(out_path.parent)

                if out_path.exists() and not args.force:
                    status = {
                        "timestamp": utc_now_iso(),
                        "source": source,
                        "document_path": str(item.document_path),
                        "output_path": str(out_path),
                        "status": "skipped_existing",
                    }
                    manifest.write(status)
                    run_summary.append(status)
                    continue

                if str(item.document_path) in known_failed and not args.retry_failed and not args.force:
                    status = {
                        "timestamp": utc_now_iso(),
                        "source": source,
                        "title": item.title,
                        "document_path": str(item.document_path),
                        "output_path": str(out_path),
                        "status": "skipped_known_error",
                    }
                    manifest.write(status)
                    run_summary.append(status)
                    continue

                try:
                    api_key, key_slot = rotator.next_key()
                    try:
                        payload = parse_one(item=item, api_key=api_key, key_slot=key_slot, args=args)
                        rotator.increment_usage(key_slot)
                    except Exception as exc:
                        if "Not authenticated" in str(exc) or "401" in str(exc) or "403" in str(exc):
                            print(f"Key slot {key_slot} failed authentication, rotating...")
                            rotator.mark_bad_key(key_slot)
                            # Re-fetch a new key and retry this specific document
                            api_key, key_slot = rotator.next_key()
                            payload = parse_one(item=item, api_key=api_key, key_slot=key_slot, args=args)
                            rotator.increment_usage(key_slot)
                        else:
                            raise exc

                    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
                    status = {
                        "timestamp": utc_now_iso(),
                        "source": source,
                        "title": item.title,
                        "document_path": str(item.document_path),
                        "output_path": str(out_path),
                        "status": "parsed",
                        "key_slot": key_slot,
                    }
                    known_failed.discard(str(item.document_path))
                except Exception as exc:  # pragma: no cover
                    status = {
                        "timestamp": utc_now_iso(),
                        "source": source,
                        "title": item.title,
                        "document_path": str(item.document_path),
                        "output_path": str(out_path),
                        "status": "error",
                        "error": str(exc),
                    }
                    retry_queue.write(status)
                    known_failed.add(str(item.document_path))
                manifest.write(status)
                run_summary.append(status)
                print(json.dumps(status, ensure_ascii=True))
        retry_queue.close()

    summary_path = output_dir / "last_run_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "completed_at": utc_now_iso(),
                "sources": args.source,
                "result_type": args.result_type,
                "output_dir": str(output_dir),
                "key_usage": rotator.usage_summary(),
                "results": run_summary,
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    print(f"Wrote run summary to {summary_path}")


if __name__ == "__main__":
    main()
