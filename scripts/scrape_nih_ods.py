from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests

from common import DEFAULT_HEADERS, DATA_DIR, ensure_dir, fetch_page, load_sources, utc_now_iso


def discover_fact_sheet_urls(list_url: str) -> list[str]:
    response = requests.get(list_url, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    urls: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        if "/factsheets/" not in href.lower():
            continue
        if "list-all" in href.lower():
            continue
        href_lower = href.lower()
        if (
            not href_lower.endswith("-consumer")
            and "-consumer/" not in href_lower
            and not href_lower.endswith("-healthprofessional")
            and "-healthprofessional/" not in href_lower
        ):
            continue
        if "datosenespanol" in href_lower:
            continue
        urls.add(urljoin(list_url, href))
    return sorted(urls)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    config = load_sources()["nih_ods"]
    raw_dir = DATA_DIR / "raw" / "nih_ods"
    ensure_dir(raw_dir)

    fact_urls = discover_fact_sheet_urls(config["seed_urls"][0])[: args.limit]
    for index, url in enumerate(fact_urls, start=1):
        page = fetch_page(url)
        slug = url.rstrip("/").split("/")[-1] or f"page-{index}"
        html_path = raw_dir / f"{slug}.html"
        meta_path = raw_dir / f"{slug}.json"
        html_path.write_text(page.html, encoding="utf-8")
        meta_path.write_text(
            json.dumps(
                {
                    "source": "nih_ods",
                    "url": page.url,
                    "fetched_at": utc_now_iso(),
                    "title": page.title,
                    "html_path": html_path.name,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[{index}] saved {url}")


if __name__ == "__main__":
    main()
