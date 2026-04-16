from __future__ import annotations

import json
from urllib.parse import urlparse

from common import CONFIG_DIR, DATA_DIR, ensure_dir, fetch_page, load_json, utc_now_iso


def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    slug = parsed.path.strip("/").replace("/", "_")
    return slug or parsed.netloc.replace(".", "_")


def main() -> None:
    config = load_json(CONFIG_DIR / "guideline_pages.json")
    for bucket, urls in config.items():
        raw_dir = DATA_DIR / "raw" / bucket
        ensure_dir(raw_dir)
        for url in urls:
            try:
                page = fetch_page(url)
            except Exception as exc:
                print(f"failed {bucket}: {url} -> {exc}")
                continue
            slug = slugify_url(url)
            html_path = raw_dir / f"{slug}.html"
            meta_path = raw_dir / f"{slug}.json"
            html_path.write_text(page.html, encoding="utf-8")
            meta_path.write_text(
                json.dumps(
                    {
                        "source": bucket,
                        "url": page.url,
                        "fetched_at": utc_now_iso(),
                        "title": page.title,
                        "html_path": html_path.name,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"saved {bucket}: {url}")


if __name__ == "__main__":
    main()
