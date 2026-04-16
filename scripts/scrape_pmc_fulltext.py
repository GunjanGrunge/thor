from __future__ import annotations

import argparse
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests

from common import DATA_DIR, DEFAULT_HEADERS, ensure_dir, utc_now_iso


IDCONV_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
EUTILS_ROOT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def load_pubmed_records() -> list[dict[str, Any]]:
    path = DATA_DIR / "raw" / "pubmed" / "reviews.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("records", [])


def idconv(pmids: list[str]) -> list[dict[str, Any]]:
    response = requests.get(
        IDCONV_URL,
        params={"ids": ",".join(pmids), "format": "json", "tool": "thor-dataset-builder"},
        headers=DEFAULT_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("records", [])


def fetch_pmc_xml(pmcid: str) -> str:
    pmc_numeric = pmcid.replace("PMC", "")
    response = requests.get(
        f"{EUTILS_ROOT}/efetch.fcgi",
        params={"db": "pmc", "id": pmc_numeric, "retmode": "xml"},
        headers=DEFAULT_HEADERS,
        timeout=60,
    )
    response.raise_for_status()
    return response.text


def title_from_xml(xml_text: str) -> str:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""
    node = root.find(".//article-title")
    return "".join(node.itertext()).strip() if node is not None else ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()

    raw_dir = DATA_DIR / "raw" / "pmc"
    ensure_dir(raw_dir)

    existing = {p.stem for p in raw_dir.glob("PMC*.json")}
    pubmed_records = load_pubmed_records()
    pmids = [str(record.get("pmid")) for record in pubmed_records if record.get("pmid")][: args.limit]

    mappings: dict[str, dict[str, Any]] = {}
    for start in range(0, len(pmids), args.batch_size):
        batch = pmids[start : start + args.batch_size]
        for record in idconv(batch):
            pmcid = record.get("pmcid")
            pmid = str(record.get("pmid") or "")
            if not pmcid or not pmid:
                continue
            mappings[pmcid] = record
        time.sleep(0.34)

    saved = 0
    index_records: list[dict[str, Any]] = []
    for pmcid, mapping in mappings.items():
        if pmcid in existing:
            meta = json.loads((raw_dir / f"{pmcid}.json").read_text(encoding="utf-8"))
            index_records.append(meta)
            continue
        try:
            xml_text = fetch_pmc_xml(pmcid)
        except Exception as exc:
            print(f"failed {pmcid}: {exc}")
            continue
        xml_path = raw_dir / f"{pmcid}.xml"
        meta_path = raw_dir / f"{pmcid}.json"
        xml_path.write_text(xml_text, encoding="utf-8")
        meta = {
            "source": "pmc",
            "pmcid": pmcid,
            "pmid": str(mapping.get("pmid") or ""),
            "doi": mapping.get("doi"),
            "fetched_at": utc_now_iso(),
            "title": title_from_xml(xml_text),
            "xml_path": xml_path.name,
            "url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        index_records.append(meta)
        saved += 1
        print(f"[{saved}] saved {pmcid}")
        time.sleep(0.34)

    manifest = {
        "source": "pmc",
        "fetched_at": utc_now_iso(),
        "count": len(index_records),
        "records": sorted(index_records, key=lambda item: item.get("pmcid", "")),
    }
    (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(index_records)} PMC records to {raw_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
