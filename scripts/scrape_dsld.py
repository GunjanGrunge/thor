from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import requests

from common import CONFIG_DIR, DATA_DIR, DEFAULT_HEADERS, ensure_dir, load_json, maybe_api_key, utc_now_iso


def dsld_get(path: str, params: dict[str, Any]) -> Any:
    api_key = maybe_api_key()
    merged = dict(params)
    if api_key:
        merged["api_key"] = api_key
    response = requests.get(
        f"https://api.ods.od.nih.gov/dsld{path}",
        params=merged,
        headers=DEFAULT_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-query", type=int, default=10)
    args = parser.parse_args()

    queries = load_json(CONFIG_DIR / "dsld_queries.json")["queries"]
    raw_dir = DATA_DIR / "raw" / "dsld"
    ensure_dir(raw_dir)

    collected: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    errors: list[dict[str, Any]] = []
    for query in queries:
        try:
            payload = dsld_get("/v9/search-filter", {"q": query, "from": 0, "size": args.per_query})
        except requests.RequestException as exc:
            errors.append({"query": query, "error": str(exc)})
            print(f"skipped query '{query}' due to DSLD error")
            continue
        hits = payload.get("hits", [])
        for hit in hits:
            src = hit.get("_source", {})
            label_id = hit.get("_id") or src.get("id")
            if not label_id or label_id in seen_ids:
                continue
            seen_ids.add(label_id)
            collected.append(
                {
                    "query": query,
                    "label_id": label_id,
                    "search_hit": hit,
                }
            )

    out_path = raw_dir / "labels.json"
    if not collected and errors and out_path.exists():
        print("no new DSLD records fetched; keeping existing labels.json")
        return
    out_path.write_text(
        json.dumps(
            {
                "source": "dsld",
                "fetched_at": utc_now_iso(),
                "queries": queries,
                "count": len(collected),
                "errors": errors,
                "records": collected,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(collected)} records to {out_path}")


if __name__ == "__main__":
    main()
