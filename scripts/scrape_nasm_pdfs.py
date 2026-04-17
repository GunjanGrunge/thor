"""Download NASM resource-center PDFs and create sidecar JSON metadata.

Saves each PDF to data/raw/nasm/<slug>.pdf with a matching <slug>.json sidecar
that is compatible with parse_visual_evidence_llamaparse.py and
parse_pdfs_nutrient.py.

Usage:
    python scripts/scrape_nasm_pdfs.py [--dry-run] [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from common import DATA_DIR, ensure_dir, utc_now_iso


RAW_DIR = DATA_DIR / "raw" / "nasm"

# All directly downloadable PDFs from https://www.nasm.org/resource-center
NASM_PDFS: list[dict[str, str]] = [
    # --- Evidence-Based Reviews ---
    {
        "url": "https://www.nasm.org/content/dam/nasm/docs/nasmlibraries/pdf/nasm-guide-to-sarcopenia-evidence-based-review.pdf",
        "title": "Guide to Sarcopenia: Evidence Based Review",
        "category": "evidence_review",
    },
    {
        "url": "https://2494739.fs1.hubspotusercontent-na1.net/hubfs/2494739/NASM%20Youth%20Resistance%20Training.pdf",
        "title": "Youth Resistance Training: Evidence Based Review",
        "category": "evidence_review",
    },
    # --- Assessment Forms ---
    {
        "url": "https://www.nasm.org/content/dam/nasm/docs/nasmlibraries/pdf/parq-plus-jan-2023-image-file.pdf",
        "title": "Physical Activity Readiness Questionnaire (PAR-Q+ 2023)",
        "category": "assessment_form",
    },
    {
        "url": "https://www.nasm.org/content/dam/nasm/docs/nasmlibraries/pdf/cpt7-lifestyle-and-health-history-handout.pdf",
        "title": "Lifestyle & Health History Handout",
        "category": "assessment_form",
    },
    {
        "url": "https://www.nasm.org/content/dam/nasm/docs/nasmlibraries/pdf/cpt7-body-composition-assessment-template.pdf",
        "title": "Body Composition Assessment Template",
        "category": "assessment_form",
    },
    {
        "url": "https://www.nasm.org/content/dam/nasm/docs/nasmlibraries/pdf/cpt7-static-dynamic-posture-assessment-template.pdf",
        "title": "Static Dynamic Posture Assessment Template",
        "category": "assessment_form",
    },
    {
        "url": "https://www.nasm.org/content/dam/nasm/docs/nasmlibraries/pdf/cpt7-cardio-assessment-template.pdf",
        "title": "Cardio Assessment Template",
        "category": "assessment_form",
    },
    # --- Programming Templates ---
    {
        "url": "https://www.nasm.org/content/dam/nasm/docs/nasmlibraries/pdf/ces-programming-template.pdf",
        "title": "CES Programming Template",
        "category": "programming_template",
    },
    {
        "url": "https://www.nasm.org/content/dam/nasm/docs/nasmlibraries/pdf/cpt7-opt-programming-template.pdf",
        "title": "OPT Programming Template",
        "category": "programming_template",
    },
    {
        "url": "https://www.nasm.org/content/dam/nasm/docs/nasmlibraries/pdf/opt-for-fitness-annual-monthly-program-design.pdf",
        "title": "OPT for Fitness: Annual & Monthly Program Design",
        "category": "programming_template",
    },
    {
        "url": "https://www.nasm.org/content/dam/nasm/docs/nasmlibraries/pdf/cpt-1rm-conversion-chart.pdf",
        "title": "One Rep Max Conversion Chart",
        "category": "programming_template",
    },
]


def slugify(url: str) -> str:
    parsed = urlparse(url)
    stem = Path(parsed.path).stem
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", stem).strip("_")
    return slug or "nasm_doc"


def download_pdf(entry: dict[str, str], out_dir: Path, client: httpx.Client, force: bool) -> bool:
    url = entry["url"]
    title = entry["title"]
    category = entry["category"]
    slug = slugify(url)

    pdf_path = out_dir / f"{slug}.pdf"
    meta_path = out_dir / f"{slug}.json"

    if pdf_path.exists() and meta_path.exists() and not force:
        print(f"  skip (exists): {title}")
        return True

    try:
        resp = client.get(url, follow_redirects=True, timeout=60.0)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(f"  HTTP {exc.response.status_code} for {url}")
        return False
    except Exception as exc:
        print(f"  error fetching {url}: {exc}")
        return False

    content_type = resp.headers.get("content-type", "")
    if "pdf" not in content_type and not url.lower().endswith(".pdf"):
        print(f"  unexpected content-type '{content_type}' for {url} — saving anyway")

    pdf_path.write_bytes(resp.content)
    meta_path.write_text(
        json.dumps(
            {
                "source": "nasm",
                "url": url,
                "fetched_at": utc_now_iso(),
                "title": title,
                "category": category,
                "pdf_path": pdf_path.name,
                "file_size_bytes": len(resp.content),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  saved ({len(resp.content) // 1024} KB): {title}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download NASM resource-center PDFs.")
    parser.add_argument("--dry-run", action="store_true", help="List PDFs without downloading.")
    parser.add_argument("--force", action="store_true", help="Re-download already saved PDFs.")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds to wait between requests (default 1.5).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dir(RAW_DIR)

    if args.dry_run:
        print(f"Dry run — {len(NASM_PDFS)} PDFs would be downloaded to {RAW_DIR}:")
        for entry in NASM_PDFS:
            print(f"  [{entry['category']}] {entry['title']}")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ThorBot/1.0)",
        "Accept": "application/pdf,*/*",
    }

    ok = failed = 0
    with httpx.Client(headers=headers) as client:
        for i, entry in enumerate(NASM_PDFS):
            print(f"[{i + 1}/{len(NASM_PDFS)}] {entry['title']}")
            if download_pdf(entry, RAW_DIR, client, args.force):
                ok += 1
            else:
                failed += 1
            if i < len(NASM_PDFS) - 1:
                time.sleep(args.delay)

    print(f"\nDone: {ok} saved, {failed} failed → {RAW_DIR}")


if __name__ == "__main__":
    main()
