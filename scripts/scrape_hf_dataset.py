from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

from common import DATA_DIR, DEFAULT_HEADERS, ensure_dir, utc_now_iso


API_ROOT = "https://datasets-server.huggingface.co"


def get_json(url: str, params: dict[str, str]) -> dict:
    response = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def pick_default_split(dataset: str) -> tuple[str, str]:
    payload = get_json(f"{API_ROOT}/splits", {"dataset": dataset})
    splits = payload.get("splits", [])
    if not splits:
        raise RuntimeError(f"No splits returned for {dataset}")
    first = splits[0]
    return first["config"], first["split"]


def fetch_rows(dataset: str, config: str, split: str, limit: int) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while len(rows) < limit:
        length = min(100, limit - len(rows))
        payload = get_json(
            f"{API_ROOT}/rows",
            {
                "dataset": dataset,
                "config": config,
                "split": split,
                "offset": str(offset),
                "length": str(length),
            },
        )
        chunk = payload.get("rows", [])
        if not chunk:
            break
        rows.extend(chunk)
        offset += len(chunk)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--output-name", required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    config, split = pick_default_split(args.dataset)
    rows = fetch_rows(args.dataset, config, split, args.limit)

    out_dir = DATA_DIR / "raw" / args.output_name
    ensure_dir(out_dir)
    out_path = out_dir / "rows.json"
    out_path.write_text(
        json.dumps(
            {
                "source": "huggingface_dataset",
                "dataset": args.dataset,
                "domain": args.domain,
                "config": config,
                "split": split,
                "fetched_at": utc_now_iso(),
                "rows": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
