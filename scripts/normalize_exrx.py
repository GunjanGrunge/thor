from __future__ import annotations

import json

from bs4 import BeautifulSoup

from common import DATA_DIR, stable_id, write_jsonl


def extract_text_blocks(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    paragraphs = []
    for tag in soup.find_all(["p", "li"]):
        text = tag.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)
    return {
        "title": title,
        "body": "\n".join(paragraphs[:200]),
    }


def main() -> None:
    raw_dir = DATA_DIR / "raw" / "exrx"
    records: list[dict] = []
    for meta_path in sorted(raw_dir.glob("*.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        html_path = raw_dir / meta["html_path"]
        html = html_path.read_text(encoding="utf-8")
        content = extract_text_blocks(html)
        records.append(
            {
                "id": stable_id("exrx", meta["url"]),
                "domain": "workout",
                "source": "exrx",
                "record_type": "exercise_reference",
                "title": content["title"] or meta["title"],
                "content": content,
                "tags": ["exercise", "form", "biomechanics"],
                "grounding_urls": [meta["url"]],
            }
        )
    write_jsonl(DATA_DIR / "normalized" / "workout_exrx.jsonl", records)
    print(f"wrote {len(records)} records")


if __name__ == "__main__":
    main()
