"""Scrape exercise and workout pages from muscleandstrength.com using Scrapling.

Follows the same pattern as scrape_musclewiki_scrapling.py:
  1. Enumerate muscle-group and equipment category pages
  2. Discover individual exercise detail links
  3. Save raw HTML + JSON metadata to data/raw/muscleandstrength/

Run via:
    wsl bash -c "cd /mnt/c/Users/Bot/Desktop/Thor && \
        VENV_DIR=/mnt/c/Users/Bot/Desktop/Thor/.venv_train \
        bash scripts/run_raw_collection_wsl.sh scrape_muscleandstrength_scrapling.py \
            --exercise-limit 600 --workout-limit 200"

Or directly:
    python scripts/scrape_muscleandstrength_scrapling.py --exercise-limit 600 --workout-limit 200
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from scrapling.fetchers import Fetcher

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BASE_URL = "https://www.muscleandstrength.com"

# Muscle-group category slugs on M&S
MUSCLE_GROUPS = [
    "abductors",
    "abs",
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
    "traps",
    "triceps",
]

# Equipment filter slugs
EQUIPMENT_TYPES = [
    "dumbbell",
    "barbell",
    "bodyweight",
    "cable",
    "machine",
]

# Workout category slugs
WORKOUT_CATEGORIES = [
    "muscle-building",
    "fat-loss",
    "strength",
    "beginner",
    "intermediate",
    "advanced",
    "men",
    "women",
    "chest",
    "back",
    "legs",
    "shoulders",
    "biceps",
    "triceps",
    "cardio",
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
        .rstrip("_")
    )


def title_from_html(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return match.group(1).strip() if match else ""


def is_ms_domain(url: str) -> bool:
    parsed = urlparse(url)
    return not parsed.netloc or "muscleandstrength.com" in parsed.netloc.lower()


def extract_exercise_links(html: str, base_url: str) -> list[str]:
    """Pull /exercises/<slug>.html detail page URLs."""
    links: set[str] = set()
    for href in re.findall(r'href="([^"#"]+)"', html, re.I):
        candidate = urljoin(base_url, href)
        if not is_ms_domain(candidate):
            continue
        parsed = urlparse(candidate)
        path = parsed.path.lower()
        # Detail pages end with .html and live under /exercises/
        if "/exercises/" in path and path.endswith(".html"):
            canonical = parsed._replace(fragment="", query="").geturl()
            links.add(canonical)
    return sorted(links)


def extract_workout_links(html: str, base_url: str) -> list[str]:
    """Pull /workouts/<slug>.html detail page URLs."""
    links: set[str] = set()
    for href in re.findall(r'href="([^"#"]+)"', html, re.I):
        candidate = urljoin(base_url, href)
        if not is_ms_domain(candidate):
            continue
        parsed = urlparse(candidate)
        path = parsed.path.lower()
        if "/workouts/" in path and path.endswith(".html"):
            canonical = parsed._replace(fragment="", query="").geturl()
            links.add(canonical)
    return sorted(links)


def save_page(
    raw_dir: Path,
    url: str,
    html: str,
    page_kind: str,
    metadata: dict | None = None,
) -> None:
    slug = slug_from_url(url)
    html_path = raw_dir / f"{slug}.html"
    meta_path = raw_dir / f"{slug}.json"
    html_path.write_text(html, encoding="utf-8")
    payload: dict = {
        "source": "muscleandstrength",
        "url": url,
        "fetched_at": utc_now_iso(),
        "title": title_from_html(html),
        "html_path": html_path.name,
        "page_kind": page_kind,
    }
    if metadata:
        payload.update(metadata)
    meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def collect_exercises(
    fetcher: Fetcher,
    raw_dir: Path,
    existing: set[str],
    limit: int,
) -> int:
    """Crawl muscle-group and equipment category pages, then scrape exercise detail pages."""
    # Build category URLs
    category_urls: list[str] = []
    for muscle in MUSCLE_GROUPS:
        category_urls.append(f"{BASE_URL}/exercises/{muscle}")
    for equip in EQUIPMENT_TYPES:
        category_urls.append(f"{BASE_URL}/exercises/{equip}")

    detail_links: set[str] = set()
    for cat_url in category_urls:
        slug = slug_from_url(cat_url)
        html_path = raw_dir / f"{slug}.html"
        if f"{slug}.json" in existing and html_path.exists():
            html = html_path.read_text(encoding="utf-8", errors="ignore")
        else:
            try:
                html = fetch_html(fetcher, cat_url)
            except Exception as exc:
                print(f"[warn] failed to fetch category {cat_url}: {exc}")
                continue
            parts = urlparse(cat_url).path.strip("/").split("/")
            save_page(
                raw_dir,
                cat_url,
                html,
                "exercise_category",
                {"muscle_or_equipment": parts[-1] if parts else ""},
            )
            existing.add(f"{slug}.json")
            print(f"[cat] {cat_url}")
        detail_links.update(extract_exercise_links(html, cat_url))

    saved = 0
    for url in sorted(detail_links)[:limit]:
        slug = slug_from_url(url)
        if f"{slug}.json" in existing and (raw_dir / f"{slug}.html").exists():
            continue
        try:
            html = fetch_html(fetcher, url)
        except Exception as exc:
            print(f"[warn] failed {url}: {exc}")
            continue
        # Extract exercise profile metadata from the page
        target_match = re.search(r"Target Muscle Group\s*([^\n<]+)", html, re.I)
        equip_match = re.search(r"Equipment Required\s*([^\n<]+)", html, re.I)
        level_match = re.search(r"Experience Level\s*([^\n<]+)", html, re.I)
        meta = {
            "target_muscle": target_match.group(1).strip() if target_match else "",
            "equipment": equip_match.group(1).strip() if equip_match else "",
            "experience_level": level_match.group(1).strip() if level_match else "",
        }
        save_page(raw_dir, url, html, "exercise_detail", meta)
        existing.add(f"{slug}.json")
        saved += 1
        print(f"[ex {saved}] {url}")
        if saved >= limit:
            break
        time.sleep(0.3)

    return saved


def collect_workouts(
    fetcher: Fetcher,
    raw_dir: Path,
    existing: set[str],
    limit: int,
) -> int:
    """Crawl workout category pages and scrape individual workout plan pages."""
    detail_links: set[str] = set()
    for cat in WORKOUT_CATEGORIES:
        cat_url = f"{BASE_URL}/workouts/{cat}"
        slug = slug_from_url(cat_url)
        html_path = raw_dir / f"{slug}.html"
        if f"{slug}.json" in existing and html_path.exists():
            html = html_path.read_text(encoding="utf-8", errors="ignore")
        else:
            try:
                html = fetch_html(fetcher, cat_url)
            except Exception as exc:
                print(f"[warn] failed workout cat {cat_url}: {exc}")
                continue
            save_page(raw_dir, cat_url, html, "workout_category", {"workout_category": cat})
            existing.add(f"{slug}.json")
            print(f"[wcat] {cat_url}")
        detail_links.update(extract_workout_links(html, cat_url))

    saved = 0
    for url in sorted(detail_links)[:limit]:
        slug = slug_from_url(url)
        if f"{slug}.json" in existing and (raw_dir / f"{slug}.html").exists():
            continue
        try:
            html = fetch_html(fetcher, url)
        except Exception as exc:
            print(f"[warn] failed {url}: {exc}")
            continue
        save_page(raw_dir, url, html, "workout_detail")
        existing.add(f"{slug}.json")
        saved += 1
        print(f"[wk {saved}] {url}")
        if saved >= limit:
            break
        time.sleep(0.3)

    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape muscleandstrength.com exercises and workouts")
    parser.add_argument("--exercise-limit", type=int, default=600, help="Max exercise detail pages to scrape")
    parser.add_argument("--workout-limit", type=int, default=200, help="Max workout plan pages to scrape")
    parser.add_argument("--skip-exercises", action="store_true", help="Skip exercise scraping")
    parser.add_argument("--skip-workouts", action="store_true", help="Skip workout scraping")
    args = parser.parse_args()

    raw_dir = DATA_DIR / "raw" / "muscleandstrength"
    ensure_dir(raw_dir)
    existing = {p.name for p in raw_dir.glob("*.json")}

    fetcher = Fetcher()

    ex_saved = 0
    if not args.skip_exercises:
        ex_saved = collect_exercises(fetcher, raw_dir, existing, args.exercise_limit)

    wk_saved = 0
    if not args.skip_workouts:
        wk_saved = collect_workouts(fetcher, raw_dir, existing, args.workout_limit)

    total = len([p for p in raw_dir.glob("*.json")])
    print(f"\nDone. Exercises saved: {ex_saved}, Workouts saved: {wk_saved}, Total pages: {total}")


if __name__ == "__main__":
    main()
