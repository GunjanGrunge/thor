from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from scrapling.fetchers import Fetcher

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "configs"
DATA_DIR = ROOT / "data"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    slug = parsed.path.strip("/").replace("/", "_")
    return slug or parsed.netloc.replace(".", "_")


def title_from_html(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return match.group(1).strip() if match else ""


def fetch_html(fetcher: Fetcher, url: str) -> str:
    response = fetcher.get(url, stealthy_headers=True)
    body = response.body
    if isinstance(body, (bytes, bytearray)):
        return body.decode("utf-8", errors="ignore")
    return str(body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    args = parser.parse_args()

    config = json.loads((CONFIG_DIR / "guideline_pages.json").read_text(encoding="utf-8"))
    urls = config.get(args.bucket, [])
    if not urls:
        raise SystemExit(f"no URLs configured for bucket {args.bucket}")

    raw_dir = DATA_DIR / "raw" / args.bucket
    ensure_dir(raw_dir)
    fetcher = Fetcher()

    for url in urls:
        html = fetch_html(fetcher, url)
        slug = slugify_url(url)
        html_path = raw_dir / f"{slug}.html"
        meta_path = raw_dir / f"{slug}.json"
        html_path.write_text(html, encoding="utf-8")
        meta_path.write_text(
            json.dumps(
                {
                    "source": args.bucket,
                    "url": url,
                    "fetched_at": utc_now_iso(),
                    "title": title_from_html(html),
                    "html_path": html_path.name,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"saved {args.bucket}: {url}")


if __name__ == "__main__":
    main()
