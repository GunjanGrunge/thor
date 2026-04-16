from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests

from common import DEFAULT_HEADERS, DATA_DIR, ensure_dir, fetch_page, load_sources, utc_now_iso


def discover_exrx_urls(seed_url: str) -> list[str]:
    response = requests.get(seed_url, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    urls: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        href_lower = href.lower()
        if href_lower.startswith("exlist/"):
            urls.add(urljoin("https://exrx.net/Lists/", href))
            continue
        if "/lists/exlist/" in href_lower:
            urls.add(urljoin(seed_url, href))
    return sorted(urls)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    config = load_sources()["exrx"]
    raw_dir = DATA_DIR / "raw" / "exrx"
    ensure_dir(raw_dir)

    urls = discover_exrx_urls(config["seed_urls"][0])[: args.limit]
    for index, url in enumerate(urls, start=1):
        page = fetch_page(url)
        slug = url.rstrip("/").replace("https://", "").replace("/", "_")
        html_path = raw_dir / f"{slug}.html"
        meta_path = raw_dir / f"{slug}.json"
        html_path.write_text(page.html, encoding="utf-8")
        meta_path.write_text(
            json.dumps(
                {
                    "source": "exrx",
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
