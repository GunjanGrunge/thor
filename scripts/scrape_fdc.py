from __future__ import annotations

import argparse
import json
from typing import Any

import requests

from common import CONFIG_DIR, DATA_DIR, DEFAULT_HEADERS, ensure_dir, load_json, maybe_env, utc_now_iso


API_ROOT = "https://api.nal.usda.gov/fdc/v1"


def fdc_get(path: str, params: dict[str, Any]) -> Any:
    api_key = maybe_env("FDC_API_KEY") or "DEMO_KEY"
    response = requests.get(
        f"{API_ROOT}{path}",
        params={"api_key": api_key},
        headers=DEFAULT_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fdc_post(path: str, payload: dict[str, Any]) -> Any:
    api_key = maybe_env("FDC_API_KEY") or "DEMO_KEY"
    headers = dict(DEFAULT_HEADERS)
    headers["Content-Type"] = "application/json"
    response = requests.post(
        f"{API_ROOT}{path}",
        params={"api_key": api_key},
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-query", type=int, default=10)
    args = parser.parse_args()

    config = load_json(CONFIG_DIR / "fdc_queries.json")
    queries = config["queries"]
    data_types = config["data_types"]

    raw_dir = DATA_DIR / "raw" / "fdc"
    ensure_dir(raw_dir)

    records: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    errors: list[dict[str, Any]] = []
    for query in queries:
        try:
            payload = fdc_post(
                "/foods/search",
                {
                    "query": query,
                    "pageSize": args.per_query,
                    "dataType": data_types,
                    "sortBy": "dataType.keyword",
                    "sortOrder": "asc",
                },
            )
        except requests.HTTPError as exc:
            response = exc.response
            errors.append(
                {
                    "query": query,
                    "status_code": response.status_code if response is not None else None,
                    "error": response.text[:1000] if response is not None else str(exc),
                }
            )
            print(f"skipped query '{query}' due to FDC error")
            continue
        foods = payload.get("foods", [])
        for food in foods:
            fdc_id = food.get("fdcId")
            if not fdc_id or fdc_id in seen_ids:
                continue
            seen_ids.add(fdc_id)
            try:
                detail = fdc_get(f"/food/{fdc_id}", {})
            except requests.HTTPError:
                detail = None
            records.append(
                {
                    "query": query,
                    "fdc_id": fdc_id,
                    "search_hit": food,
                    "detail": detail,
                }
            )

    out_path = raw_dir / "foods.json"
    out_path.write_text(
        json.dumps(
            {
                "source": "fdc",
                "fetched_at": utc_now_iso(),
                "queries": queries,
                "data_types": data_types,
                "count": len(records),
                "errors": errors,
                "records": records,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(records)} records to {out_path}")


if __name__ == "__main__":
    main()
