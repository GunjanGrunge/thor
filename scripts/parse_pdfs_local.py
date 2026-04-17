import os
import fitz  # PyMuPDF
import json
from pathlib import Path
from datetime import datetime, timezone

# Configuration
RAW_DIR = Path(r"c:\Users\Bot\Desktop\Thor\data\raw\external_nutrition")
PARSED_DIR = Path(r"c:\Users\Bot\Desktop\Thor\data\parsed\local_fitz")
PARSED_DIR.mkdir(parents=True, exist_ok=True)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def parse_local(pdf_path: Path):
    sidecar_path = pdf_path.with_suffix(".json")
    if not sidecar_path.exists():
        print(f"Skipping {pdf_path.name} (no sidecar)")
        return

    with open(sidecar_path, 'r') as f:
        metadata = json.load(f)

    print(f"Parsing {pdf_path.name} locally with fitz...")
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n\n"
        
        result = {
            "parsed_at": utc_now_iso(),
            "parser": {"provider": "local_fitz", "key_slot": 0},
            "source_document": {
                "source": "external_nutrition",
                "title": metadata.get("title") or pdf_path.stem,
                "url": metadata.get("url", ""),
                "document_path": str(pdf_path),
                "sidecar_path": str(sidecar_path),
                "metadata": {k: v for k, v in metadata.items() if k not in {"title", "url", "pdf_path"}},
            },
            "documents": [
                {
                    "index": 0,
                    "text": full_text,
                    "metadata": {},
                    "doc_id": None,
                }
            ],
        }

        out_source_dir = PARSED_DIR / "external_nutrition"
        out_source_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_source_dir / f"{pdf_path.stem}.json"
        
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully saved {len(full_text)} chars to {out_file}")
    except Exception as e:
        print(f"Error parsing {pdf_path.name}: {e}")

if __name__ == "__main__":
    for pdf_file in RAW_DIR.glob("*.pdf"):
        # Check if already parsed by Nutrient (to avoid duplicates)
        # Actually, I'll just parse all missing ones
        parse_local(pdf_file)
