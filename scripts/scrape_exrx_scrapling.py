from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from scrapling.fetchers import Fetcher

ROOT_URL = "https://exrx.net/Lists/Directory"
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


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


def extract_exlist_links(html: str, base_url: str) -> list[str]:
    links = set()
    for href in re.findall(r'href="([^"]+)"', html, re.I):
        href_lower = href.lower()
        if "exlist/" not in href_lower:
            continue
        links.add(urljoin(base_url, href))
    return sorted(links)


def extract_detail_links(html: str, base_url: str) -> list[str]:
    patterns = (
        "/weightexercises/",
        "/stretches/",
        "/aerobic/",
        "/exinfo/",
    )
    blocked_suffixes = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".pdf")
    links = set()
    for href in re.findall(r'href="([^"]+)"', html, re.I):
        candidate = urljoin(base_url, href)
        parsed = urlparse(candidate)
        path = parsed.path.lower()
        if parsed.netloc and parsed.netloc.lower() != "exrx.net":
            continue
        if "${" in candidate or "}" in candidate:
            continue
        if not any(pattern in path for pattern in patterns):
            continue
        if path.endswith(blocked_suffixes):
            continue
        canonical = parsed._replace(fragment="", query="").geturl().replace("http://", "https://")
        links.add(canonical)
    return sorted(links)


def title_from_html(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return match.group(1).strip() if match else ""


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


def save_page(raw_dir: Path, url: str, html: str) -> None:
    slug = slug_from_url(url)
    html_path = raw_dir / f"{slug}.html"
    meta_path = raw_dir / f"{slug}.json"
    html_path.write_text(html, encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "source": "exrx_scrapling",
                "url": url,
                "fetched_at": utc_now_iso(),
                "title": title_from_html(html),
                "html_path": html_path.name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--detail-limit", type=int, default=500)
    parser.add_argument("--depth", type=int, default=2)
    args = parser.parse_args()

    raw_dir = DATA_DIR / "raw" / "exrx"
    ensure_dir(raw_dir)

    fetcher = Fetcher()
    directory_html = fetch_html(fetcher, ROOT_URL)
    save_page(raw_dir, ROOT_URL, directory_html)

    links = extract_exlist_links(directory_html, ROOT_URL)[: args.limit]
    existing = {p.name for p in raw_dir.glob("*.json")}
    saved = 0
    detail_links: set[str] = set()
    for url in links:
        slug = slug_from_url(url)
        if f"{slug}.json" in existing:
            html_path = raw_dir / f"{slug}.html"
            html = html_path.read_text(encoding="utf-8", errors="ignore") if html_path.exists() else ""
        else:
            html = fetch_html(fetcher, url)
            save_page(raw_dir, url, html)
            existing.add(f"{slug}.json")
            saved += 1
            print(f"[{saved}] saved index {url}")
        detail_links.update(extract_detail_links(html, url))

    detail_saved = 0
    frontier = sorted(detail_links)[: args.detail_limit]
    seen_detail_links = set(frontier)
    for _ in range(max(1, args.depth)):
        next_frontier: list[str] = []
        for url in frontier:
            slug = slug_from_url(url)
            html_path = raw_dir / f"{slug}.html"
            if f"{slug}.json" in existing and html_path.exists():
                html = html_path.read_text(encoding="utf-8", errors="ignore")
            else:
                html = fetch_html(fetcher, url)
                save_page(raw_dir, url, html)
                existing.add(f"{slug}.json")
                detail_saved += 1
                print(f"[{detail_saved}] saved detail {url}")
            for discovered in extract_detail_links(html, url):
                if discovered in seen_detail_links:
                    continue
                seen_detail_links.add(discovered)
                if len(seen_detail_links) <= args.detail_limit:
                    next_frontier.append(discovered)
        frontier = next_frontier
        if not frontier or len(seen_detail_links) >= args.detail_limit:
            break


if __name__ == "__main__":
    main()
