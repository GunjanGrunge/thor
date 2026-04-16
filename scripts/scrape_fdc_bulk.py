from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from common import CONFIG_DIR, DATA_DIR, DEFAULT_HEADERS, ensure_dir, load_json, utc_now_iso


def discover_dataset_links(page_url: str, targets: list[dict[str, str]]) -> list[dict[str, str]]:
    response = requests.get(page_url, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    discovered: list[dict[str, str]] = []

    for target in targets:
        matches: list[dict[str, str]] = []
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "").strip()
            text = anchor.get_text(" ", strip=True)
            if not href or ".zip" not in href.lower():
                continue
            if target["pattern"].lower() not in href.lower():
                continue
            matches.append(
                {
                    "dataset": target["name"],
                    "url": urljoin(page_url, href),
                    "label": text or href,
                }
            )
        if matches:
            discovered.append(matches[0])
    return discovered


def download_file(url: str, dest: Path) -> None:
    with requests.get(url, headers=DEFAULT_HEADERS, timeout=120, stream=True) as response:
        response.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def main() -> None:
    config = load_json(CONFIG_DIR / "fdc_bulk_targets.json")
    raw_dir = DATA_DIR / "raw" / "fdc_bulk"
    ensure_dir(raw_dir)

    links = discover_dataset_links(config["page_url"], config["datasets"])
    manifest: list[dict[str, str | int]] = []
    for item in links:
        dataset_slug = item["dataset"].lower().replace(" ", "_").replace("(", "").replace(")", "")
        filename = item["url"].split("/")[-1].split("?")[0] or f"{dataset_slug}.zip"
        dest = raw_dir / filename
        if not dest.exists():
            download_file(item["url"], dest)
        manifest.append(
            {
                "dataset": item["dataset"],
                "url": item["url"],
                "filename": filename,
                "size_bytes": dest.stat().st_size,
            }
        )
        print(f"saved {item['dataset']} -> {filename}")

    manifest_path = raw_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source": "fdc_bulk",
                "fetched_at": utc_now_iso(),
                "page_url": config["page_url"],
                "downloads": manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
