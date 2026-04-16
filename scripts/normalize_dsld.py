from __future__ import annotations

import json

from common import DATA_DIR, stable_id, write_jsonl


def pick_label_source(record: dict) -> dict:
    label = record.get("label")
    if isinstance(label, dict) and label.get("_source"):
        return label["_source"]
    return record["search_hit"].get("_source", {})


def main() -> None:
    raw_path = DATA_DIR / "raw" / "dsld" / "labels.json"
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    normalized: list[dict] = []

    for item in payload.get("records", []):
        src = pick_label_source(item)
        label_id = item.get("label_id") or src.get("id")
        title = src.get("fullName") or src.get("brandName") or "unknown supplement"
        ingredients = src.get("allIngredients", [])
        normalized.append(
            {
                "id": stable_id("dsld", str(label_id)),
                "domain": "supplements",
                "source": "dsld",
                "record_type": "supplement_label",
                "title": title,
                "content": {
                    "label_id": label_id,
                    "brand_name": src.get("brandName"),
                    "full_name": src.get("fullName"),
                    "servings_per_container": src.get("servingsPerContainer"),
                    "net_contents": src.get("netContents"),
                    "serving_sizes": src.get("servingSizes"),
                    "ingredients": ingredients,
                    "claims": src.get("claims"),
                    "warnings": src.get("warningStatements"),
                    "directions": src.get("directions"),
                },
                "tags": ["supplement", "label", item["query"]],
                "grounding_urls": [f"https://api.ods.od.nih.gov/dsld/v9/label/{label_id}"],
            }
        )

    write_jsonl(DATA_DIR / "normalized" / "supplements_dsld.jsonl", normalized)
    print(f"wrote {len(normalized)} records")


if __name__ == "__main__":
    main()
