from __future__ import annotations

import json
import zipfile
from pathlib import Path

from common import DATA_DIR, ensure_dir, utc_now_iso


def main() -> None:
    bulk_dir = DATA_DIR / "raw" / "fdc_bulk"
    extracted_dir = DATA_DIR / "raw" / "fdc_bulk_extracted"
    ensure_dir(extracted_dir)

    manifest: list[dict[str, object]] = []
    for zip_path in sorted(bulk_dir.glob("*.zip")):
        dataset_dir = extracted_dir / zip_path.stem
        ensure_dir(dataset_dir)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(dataset_dir)
            manifest.append(
                {
                    "zip": zip_path.name,
                    "target_dir": dataset_dir.name,
                    "member_count": len(archive.infolist()),
                }
            )
        print(f"extracted {zip_path.name}")

    out_path = extracted_dir / "manifest.json"
    out_path.write_text(
        json.dumps(
            {
                "source": "fdc_bulk_extracted",
                "extracted_at": utc_now_iso(),
                "datasets": manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
