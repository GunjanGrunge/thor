from __future__ import annotations

import json
from pathlib import Path

from bs4 import BeautifulSoup

from common import DATA_DIR, stable_id, write_jsonl


def extract_sections(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    sections: dict[str, str] = {}
    current_heading = "overview"
    sections[current_heading] = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        if tag.name in {"h1", "h2", "h3"}:
            current_heading = tag.get_text(" ", strip=True).lower()
            sections.setdefault(current_heading, [])
            continue
        text = tag.get_text(" ", strip=True)
        if text:
            sections.setdefault(current_heading, []).append(text)
    return {key: "\n".join(value) for key, value in sections.items() if value}


def main() -> None:
    raw_dir = DATA_DIR / "raw" / "nih_ods"
    records: list[dict] = []
    for meta_path in sorted(raw_dir.glob("*.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        html_path = raw_dir / meta["html_path"]
        html = html_path.read_text(encoding="utf-8")
        records.append(
            {
                "id": stable_id("nihods", meta["url"]),
                "domain": "supplements",
                "source": "nih_ods",
                "record_type": "fact_sheet",
                "title": meta["title"],
                "content": extract_sections(html),
                "tags": ["supplement", "safety", "evidence"],
                "grounding_urls": [meta["url"]],
            }
        )
    write_jsonl(DATA_DIR / "normalized" / "supplements_nih_ods.jsonl", records)
    print(f"wrote {len(records)} records")


if __name__ == "__main__":
    main()
