from __future__ import annotations

import json
from pathlib import Path

TARGETS = [
    "https://exrx.net/Lists/Directory",
    "https://dsld.od.nih.gov/api-guide",
]


def main() -> None:
    results = []
    try:
        from scrapling.fetchers import Fetcher
    except Exception as exc:
        print(json.dumps({"error": f"import_failed: {exc}"}, indent=2))
        raise

    for url in TARGETS:
        record = {"url": url}
        try:
            fetcher = Fetcher(auto_match=False)
            response = fetcher.get(url, stealthy_headers=True)
            text = getattr(response, "text", "") or ""
            status = getattr(response, "status", None)
            record["status"] = status
            record["text_preview"] = text[:1500]
            lowered = text.lower()
            record["blocked_marker"] = any(
                needle in lowered
                for needle in [
                    "sorry, you have been blocked",
                    "please enable cookies",
                    "attention required",
                ]
            )
        except Exception as exc:
            record["error"] = str(exc)
        results.append(record)

    out_path = Path("data") / "raw" / "scrapling_test_results.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
