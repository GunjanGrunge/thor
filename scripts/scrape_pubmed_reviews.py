from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from typing import Any

import requests

from common import CONFIG_DIR, DATA_DIR, DEFAULT_HEADERS, ensure_dir, load_json, utc_now_iso


API_ROOT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def eutils_get(path: str, params: dict[str, Any]) -> requests.Response:
    response = requests.get(f"{API_ROOT}/{path}", params=params, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()
    return response


def search_pmids(query: str, limit: int) -> list[str]:
    response = eutils_get(
        "esearch.fcgi",
        {
            "db": "pubmed",
            "term": query,
            "retmax": limit,
            "retmode": "json",
            "sort": "relevance",
        },
    ).json()
    return response.get("esearchresult", {}).get("idlist", [])


def fetch_pubmed_xml(pmids: list[str]) -> ET.Element:
    response = eutils_get(
        "efetch.fcgi",
        {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        },
    )
    return ET.fromstring(response.text)


def parse_article(article: ET.Element) -> dict[str, Any]:
    medline = article.find("MedlineCitation")
    article_info = medline.find("Article") if medline is not None else None
    pmid = medline.findtext("PMID") if medline is not None else None
    title = article_info.findtext("ArticleTitle") if article_info is not None else None
    abstract_text = []
    if article_info is not None:
        abstract = article_info.find("Abstract")
        if abstract is not None:
            for node in abstract.findall("AbstractText"):
                label = node.attrib.get("Label")
                text = "".join(node.itertext()).strip()
                if not text:
                    continue
                abstract_text.append({"label": label, "text": text})
    journal = article_info.find("Journal") if article_info is not None else None
    pub_date = None
    if journal is not None:
        issue = journal.find("JournalIssue")
        if issue is not None:
            pub_date = "".join(issue.find("PubDate").itertext()).strip() if issue.find("PubDate") is not None else None
    publication_types = []
    if article_info is not None:
        for node in article_info.findall("PublicationTypeList/PublicationType"):
            text = "".join(node.itertext()).strip()
            if text:
                publication_types.append(text)
    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract_text,
        "publication_types": publication_types,
        "journal": journal.findtext("Title") if journal is not None else None,
        "pub_date": pub_date,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-query", type=int, default=10)
    args = parser.parse_args()

    queries = load_json(CONFIG_DIR / "pubmed_queries.json")["queries"]
    raw_dir = DATA_DIR / "raw" / "pubmed"
    ensure_dir(raw_dir)

    out_path = raw_dir / "reviews.json"
    existing_by_pmid: dict[str, dict[str, Any]] = {}
    if out_path.exists():
        existing_payload = json.loads(out_path.read_text(encoding="utf-8"))
        for record in existing_payload.get("records", []):
            pmid = str(record.get("pmid") or "")
            if pmid:
                existing_by_pmid[pmid] = record

    all_records: list[dict[str, Any]] = list(existing_by_pmid.values())
    for query in queries:
        try:
            pmids = search_pmids(query, args.per_query)
            if not pmids:
                continue
            root = fetch_pubmed_xml(pmids)
        except Exception as exc:
            print(f"failed query: {query} -> {exc}")
            continue
        for article in root.findall("PubmedArticle"):
            parsed = parse_article(article)
            parsed["query"] = query
            pmid = str(parsed.get("pmid") or "")
            if not pmid:
                continue
            if pmid in existing_by_pmid:
                continue
            existing_by_pmid[pmid] = parsed
            all_records.append(parsed)

    out_path.write_text(
        json.dumps(
            {
                "source": "pubmed",
                "fetched_at": utc_now_iso(),
                "queries": queries,
                "count": len(all_records),
                "records": all_records,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(all_records)} records to {out_path}")


if __name__ == "__main__":
    main()
