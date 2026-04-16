from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from scrapling.fetchers import Fetcher


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BASE_URL = "https://musclewiki.com"

MUSCLES = [
    "abdominals",
    "adductors",
    "biceps",
    "calves",
    "chest",
    "forearms",
    "glutes",
    "hamstrings",
    "lats",
    "lower-back",
    "middle-back",
    "neck",
    "obliques",
    "quadriceps",
    "shoulders",
    "trapezius",
    "triceps",
]

EQUIPMENT = [
    "bodyweight",
    "dumbbells",
    "barbell",
    "cables",
    "machines",
    "kettlebells",
    "bands",
    "smith-machine",
    "ez-bar",
    "medicine-ball",
    "trx",
    "stretches",
    "bench",
    "bosu-ball",
    "foam-roll",
    "hex-bar",
    "plate",
    "resistance-band",
    "slam-ball",
    "stability-ball",
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_html(fetcher: Fetcher, url: str) -> str:
    response = fetcher.get(url, stealthy_headers=True)
    body = response.body
    if isinstance(body, (bytes, bytearray)):
        return body.decode("utf-8", errors="ignore")
    return str(body)


def slug_from_url(url: str) -> str:
    return (
        url.replace("https://", "")
        .replace("http://", "")
        .replace("/", "_")
        .replace("?", "_")
        .replace("&", "_")
        .replace("=", "_")
        .replace("#", "_")
    )


def title_from_html(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return match.group(1).strip() if match else ""


def extract_exercise_links(html: str, base_url: str) -> list[str]:
    links = set()
    for href in re.findall(r'href="([^"]+)"', html, re.I):
        candidate = urljoin(base_url, href)
        parsed = urlparse(candidate)
        if parsed.netloc and parsed.netloc.lower() != "musclewiki.com":
            continue
        if "/exercise/" not in parsed.path.lower():
            continue
        links.add(candidate)
    return sorted(links)


def extract_category_links(html: str, base_url: str) -> list[str]:
    links = set()
    for href in re.findall(r'href="([^"]+)"', html, re.I):
        candidate = urljoin(base_url, href)
        parsed = urlparse(candidate)
        if parsed.netloc and parsed.netloc.lower() != "musclewiki.com":
            continue
        if "/exercises/" not in parsed.path.lower():
            continue
        links.add(candidate)
    return sorted(links)


def save_page(raw_dir: Path, url: str, html: str, page_kind: str, metadata: dict[str, str] | None = None) -> None:
    slug = slug_from_url(url)
    html_path = raw_dir / f"{slug}.html"
    meta_path = raw_dir / f"{slug}.json"
    html_path.write_text(html, encoding="utf-8")
    payload = {
        "source": "musclewiki_scrapling",
        "url": url,
        "fetched_at": utc_now_iso(),
        "title": title_from_html(html),
        "html_path": html_path.name,
        "page_kind": page_kind,
    }
    if metadata:
        payload.update(metadata)
    meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category-limit", type=int, default=200)
    parser.add_argument("--detail-limit", type=int, default=1000)
    parser.add_argument("--depth", type=int, default=2)
    args = parser.parse_args()

    raw_dir = DATA_DIR / "raw" / "musclewiki"
    ensure_dir(raw_dir)
    existing = {p.name for p in raw_dir.glob("*.json")}
    fetcher = Fetcher()

    category_urls = [
        f"{BASE_URL}/exercises/{muscle}/{equipment}"
        for muscle in MUSCLES
        for equipment in EQUIPMENT
    ][: args.category_limit]

    discovered_categories = set(category_urls)
    detail_links: set[str] = set()
    category_saved = 0
    category_frontier = category_urls
    for _ in range(max(1, args.depth)):
        next_categories: list[str] = []
        for url in category_frontier:
            slug = slug_from_url(url)
            html_path = raw_dir / f"{slug}.html"
            if f"{slug}.json" in existing and html_path.exists():
                html = html_path.read_text(encoding="utf-8", errors="ignore")
            else:
                html = fetch_html(fetcher, url)
                links = extract_exercise_links(html, url)
                if not links:
                    continue
                parts = urlparse(url).path.strip("/").split("/")
                metadata = {
                    "muscle": parts[1] if len(parts) > 1 else "",
                    "equipment": parts[2] if len(parts) > 2 else "",
                }
                save_page(raw_dir, url, html, "category", metadata)
                existing.add(f"{slug}.json")
                category_saved += 1
                print(f"[{category_saved}] saved category {url}")
            detail_links.update(extract_exercise_links(html, url))
            for discovered in extract_category_links(html, url):
                if discovered in discovered_categories:
                    continue
                discovered_categories.add(discovered)
                if len(discovered_categories) <= args.category_limit:
                    next_categories.append(discovered)
        category_frontier = next_categories
        if not category_frontier or len(discovered_categories) >= args.category_limit:
            break

    detail_saved = 0
    detail_frontier = sorted(detail_links)[: args.detail_limit]
    seen_details = set(detail_frontier)
    for _ in range(max(1, args.depth)):
        next_details: list[str] = []
        for url in detail_frontier:
            slug = slug_from_url(url)
            html_path = raw_dir / f"{slug}.html"
            if f"{slug}.json" in existing and html_path.exists():
                html = html_path.read_text(encoding="utf-8", errors="ignore")
            else:
                html = fetch_html(fetcher, url)
                save_page(raw_dir, url, html, "exercise")
                existing.add(f"{slug}.json")
                detail_saved += 1
                print(f"[{detail_saved}] saved detail {url}")
            for discovered in extract_exercise_links(html, url):
                if discovered in seen_details:
                    continue
                seen_details.add(discovered)
                if len(seen_details) <= args.detail_limit:
                    next_details.append(discovered)
        detail_frontier = next_details
        if not detail_frontier or len(seen_details) >= args.detail_limit:
            break


if __name__ == "__main__":
    main()
