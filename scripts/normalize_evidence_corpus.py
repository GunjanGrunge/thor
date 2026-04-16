from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
import jsonlines

from common import DATA_DIR, stable_id, write_jsonl


RAW_DIR = DATA_DIR / "raw"
NORM_DIR = DATA_DIR / "normalized"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def html_to_text_and_sections(html: str) -> tuple[str, dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    sections: dict[str, list[str]] = {}
    current = "overview"
    sections[current] = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        if tag.name in {"h1", "h2", "h3"}:
            heading = clean_whitespace(tag.get_text(" ", strip=True)).lower()
            current = heading or current
            sections.setdefault(current, [])
            continue
        text = clean_whitespace(tag.get_text(" ", strip=True))
        if text:
            sections.setdefault(current, []).append(text)
    text = clean_whitespace(soup.get_text(" ", strip=True))
    return text, {k: "\n".join(v[:50]) for k, v in sections.items() if v}


def compact_sections(sections: dict[str, str], limit: int = 12) -> dict[str, str]:
    items = list(sections.items())[:limit]
    return {k: v[:4000] for k, v in items}


def nutrient_map(food_nutrients: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    selected = {
        "Energy",
        "Protein",
        "Total lipid (fat)",
        "Carbohydrate, by difference",
        "Fiber, total dietary",
        "Total Sugars",
        "Calcium, Ca",
        "Iron, Fe",
        "Magnesium, Mg",
        "Phosphorus, P",
        "Potassium, K",
        "Sodium, Na",
        "Zinc, Zn",
        "Vitamin C, total ascorbic acid",
        "Vitamin D (D2 + D3)",
        "Vitamin B-12",
        "Vitamin A, RAE",
    }
    out: dict[str, dict[str, Any]] = {}
    for item in food_nutrients:
        nutrient = item.get("nutrient", {})
        name = nutrient.get("name")
        if name not in selected:
            continue
        out[name] = {
            "amount": item.get("amount"),
            "unit": nutrient.get("unitName"),
            "number": nutrient.get("number"),
        }
    return out


def normalize_fdc() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    mapping = [
        (
            RAW_DIR / "fdc_bulk_extracted" / "FoodData_Central_foundation_food_json_2025-12-18" / "FoodData_Central_foundation_food_json_2025-12-18.json",
            "FoundationFoods",
            "foundation",
        ),
        (
            RAW_DIR / "fdc_bulk_extracted" / "FoodData_Central_sr_legacy_food_json_2018-04" / "FoodData_Central_sr_legacy_food_json_2018-04.json",
            "SRLegacyFoods",
            "sr_legacy",
        ),
        (
            RAW_DIR / "fdc_bulk_extracted" / "FoodData_Central_survey_food_json_2024-10-31" / "surveyDownload.json",
            "SurveyFoods",
            "survey_fndds",
        ),
    ]
    for path, root_key, source_variant in mapping:
        if not path.exists():
            continue
        payload = json.loads(load_text(path))
        foods = payload.get(root_key, [])
        for food in foods:
            description = food.get("description") or "unknown food"
            fdc_id = food.get("fdcId")
            content = {
                "fdc_id": fdc_id,
                "description": description,
                "data_type": food.get("dataType"),
                "food_class": food.get("foodClass"),
                "nutrients": nutrient_map(food.get("foodNutrients", [])),
                "portions": food.get("foodPortions", [])[:10],
                "publication_date": food.get("publicationDate"),
                "food_category": food.get("wweiaFoodCategory"),
            }
            records.append(
                {
                    "id": stable_id("fdc", f"{source_variant}:{fdc_id}:{description}"),
                    "domain": "nutrition",
                    "source": "fdc",
                    "record_type": "food_reference",
                    "title": description,
                    "summary": clean_whitespace(description),
                    "content": content,
                    "tags": ["nutrition", "food", source_variant],
                    "grounding_urls": [f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{fdc_id}"],
                    "metadata": {"source_variant": source_variant},
                }
            )
    return records


def normalize_nih_ods() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for meta_path in sorted((RAW_DIR / "nih_ods").glob("*.json")):
        meta = json.loads(load_text(meta_path))
        html_path = meta_path.with_name(meta["html_path"])
        text, sections = html_to_text_and_sections(load_text(html_path))
        title = meta.get("title") or meta_path.stem
        domain = "workout" if "athletic performance" in title.lower() else "supplements"
        records.append(
            {
                "id": stable_id("nihods", meta["url"]),
                "domain": domain,
                "source": "nih_ods",
                "record_type": "fact_sheet",
                "title": title,
                "summary": text[:500],
                "content": {
                    "sections": compact_sections(sections),
                    "text": text[:12000],
                },
                "tags": ["nih", "supplement", "fact_sheet"],
                "grounding_urls": [meta["url"]],
                "metadata": {"page_type": "health_professional" if "healthprofessional" in meta["url"].lower() else "consumer"},
            }
        )
    return records


def normalize_dsld() -> list[dict[str, Any]]:
    payload = json.loads(load_text(RAW_DIR / "dsld" / "labels.json"))
    records: list[dict[str, Any]] = []
    for item in payload.get("records", []):
        src = item.get("search_hit", {}).get("_source", {})
        label_id = item.get("label_id")
        title = src.get("fullName") or src.get("brandName") or f"label {label_id}"
        records.append(
            {
                "id": stable_id("dsld", str(label_id)),
                "domain": "supplements",
                "source": "dsld",
                "record_type": "supplement_label",
                "title": title,
                "summary": clean_whitespace(f"{src.get('brandName', '')} {src.get('fullName', '')}"),
                "content": {
                    "label_id": label_id,
                    "brand_name": src.get("brandName"),
                    "full_name": src.get("fullName"),
                    "entry_date": src.get("entryDate"),
                    "ingredients": src.get("allIngredients", [])[:100],
                    "claims": src.get("claims"),
                    "net_contents": src.get("netContents"),
                    "product_type": src.get("productType"),
                    "off_market": src.get("offMarket"),
                },
                "tags": ["supplement", "label", item.get("query", "")],
                "grounding_urls": [f"https://api.ods.od.nih.gov/dsld/v9/label/{label_id}"],
                "metadata": {"query": item.get("query")},
            }
        )
    return records


def normalize_exrx() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for meta_path in sorted((RAW_DIR / "exrx").glob("*.json")):
        meta = json.loads(load_text(meta_path))
        html_path = meta_path.with_name(meta["html_path"])
        text, sections = html_to_text_and_sections(load_text(html_path))
        title = meta.get("title") or meta_path.stem
        url = meta["url"]
        url_lower = url.lower()
        if "${" in url or "}" in url:
            continue
        is_detail = any(token in url_lower for token in ("/weightexercises/", "/stretches/", "/aerobic/", "/exinfo/"))
        records.append(
            {
                "id": stable_id("exrx", url),
                "domain": "workout",
                "source": "exrx",
                "record_type": "exercise_detail_page" if is_detail else "exercise_directory_page",
                "title": title,
                "summary": text[:500],
                "content": {
                    "sections": compact_sections(sections),
                    "text": text[:12000],
                },
                "tags": ["workout", "exercise", "secondary_source", "detail_page" if is_detail else "index_page"],
                "grounding_urls": [url],
                "metadata": {"page_kind": "detail" if is_detail else "index"},
            }
        )
    return records


def normalize_page_bucket(bucket: str, source_name: str, domain: str, record_type: str, tags: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for meta_path in sorted((RAW_DIR / bucket).glob("*.json")):
        meta = json.loads(load_text(meta_path))
        html_path = meta_path.with_name(meta["html_path"])
        text, sections = html_to_text_and_sections(load_text(html_path))
        records.append(
            {
                "id": stable_id(source_name, meta["url"]),
                "domain": domain,
                "source": source_name,
                "record_type": record_type,
                "title": meta.get("title") or meta_path.stem,
                "summary": text[:500],
                "content": {
                    "sections": compact_sections(sections),
                    "text": text[:12000],
                },
                "tags": tags,
                "grounding_urls": [meta["url"]],
                "metadata": {},
            }
        )
    return records


def normalize_musclewiki() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for meta_path in sorted((RAW_DIR / "musclewiki").glob("*.json")):
        if meta_path.name == "manifest.json":
            continue
        meta = json.loads(load_text(meta_path))
        html_path = meta_path.with_name(meta["html_path"])
        text, sections = html_to_text_and_sections(load_text(html_path))
        page_kind = meta.get("page_kind") or "unknown"
        records.append(
            {
                "id": stable_id("musclewiki", meta["url"]),
                "domain": "workout",
                "source": "musclewiki",
                "record_type": "exercise_detail_page" if page_kind == "exercise" else "exercise_category_page",
                "title": meta.get("title") or meta_path.stem,
                "summary": text[:500],
                "content": {
                    "sections": compact_sections(sections),
                    "text": text[:12000],
                    "muscle": meta.get("muscle"),
                    "equipment": meta.get("equipment"),
                },
                "tags": ["workout", "exercise", "secondary_source", "musclewiki", page_kind],
                "grounding_urls": [meta["url"]],
                "metadata": {"page_kind": page_kind},
            }
        )
    return records


def normalize_pubmed() -> list[dict[str, Any]]:
    payload = json.loads(load_text(RAW_DIR / "pubmed" / "reviews.json"))
    records: list[dict[str, Any]] = []
    for article in payload.get("records", []):
        abstract_parts = article.get("abstract", [])
        summary = " ".join(part.get("text", "") for part in abstract_parts)[:1500]
        records.append(
            {
                "id": stable_id("pubmed", str(article.get("pmid"))),
                "domain": "science",
                "source": "pubmed",
                "record_type": "scientific_review",
                "title": article.get("title") or f"PMID {article.get('pmid')}",
                "summary": summary,
                "content": {
                    "pmid": article.get("pmid"),
                    "journal": article.get("journal"),
                    "pub_date": article.get("pub_date"),
                    "publication_types": article.get("publication_types", []),
                    "abstract": abstract_parts,
                    "query": article.get("query"),
                },
                "tags": ["science", "pubmed", "review"],
                "grounding_urls": [f"https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid')}/"],
                "metadata": {"query": article.get("query")},
            }
        )
    return records


def normalize_pmc() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    raw_dir = RAW_DIR / "pmc"
    for meta_path in sorted(raw_dir.glob("PMC*.json")):
        meta = json.loads(load_text(meta_path))
        xml_path = meta_path.with_name(meta["xml_path"])
        soup = BeautifulSoup(load_text(xml_path), "xml")
        sections: dict[str, str] = {}
        body = soup.find("body")
        if body is not None:
            for sec in body.find_all("sec"):
                title_node = sec.find("title")
                heading = clean_whitespace(title_node.get_text(" ", strip=True)) if title_node else "section"
                paragraphs = [
                    clean_whitespace(node.get_text(" ", strip=True))
                    for node in sec.find_all("p")
                ]
                paragraphs = [paragraph for paragraph in paragraphs if paragraph]
                if paragraphs and heading not in sections:
                    sections[heading] = "\n".join(paragraphs[:20])
        body_text = clean_whitespace(body.get_text(" ", strip=True)) if body is not None else ""
        records.append(
            {
                "id": stable_id("pmc", meta["pmcid"]),
                "domain": "science",
                "source": "pmc",
                "record_type": "scientific_fulltext",
                "title": meta.get("title") or meta["pmcid"],
                "summary": body_text[:1500],
                "content": {
                    "pmcid": meta.get("pmcid"),
                    "pmid": meta.get("pmid"),
                    "doi": meta.get("doi"),
                    "sections": compact_sections(sections),
                    "text": body_text[:20000],
                },
                "tags": ["science", "pmc", "fulltext"],
                "grounding_urls": [meta["url"]],
                "metadata": {"pmid": meta.get("pmid"), "doi": meta.get("doi")},
            }
        )
    return records


def write_source_file(name: str, records: list[dict[str, Any]]) -> None:
    write_jsonl(NORM_DIR / f"evidence_{name}.jsonl", records)
    print(f"wrote {len(records)} records to evidence_{name}.jsonl")


def write_merged(records_by_source: dict[str, list[dict[str, Any]]]) -> None:
    merged = []
    for records in records_by_source.values():
        merged.extend(records)
    write_jsonl(NORM_DIR / "evidence_all.jsonl", merged)
    print(f"wrote {len(merged)} records to evidence_all.jsonl")

    counts = [{"source": source, "count": len(records)} for source, records in records_by_source.items()]
    with jsonlines.open(NORM_DIR / "evidence_manifest.jsonl", mode="w") as writer:
        writer.write_all(counts)


def main() -> None:
    records_by_source = {
        "fdc": normalize_fdc(),
        "nih_ods": normalize_nih_ods(),
        "dsld": normalize_dsld(),
        "exrx": normalize_exrx(),
        "musclewiki": normalize_musclewiki(),
        "cdc": normalize_page_bucket("cdc_guidelines", "cdc", "guidelines", "guideline_page", ["guidelines", "workout", "cdc"]),
        "medlineplus": normalize_page_bucket("medlineplus", "medlineplus", "guidelines", "reference_page", ["guidelines", "nutrition", "workout", "medlineplus"]),
        "who": normalize_page_bucket("who_guidelines", "who", "guidelines", "guideline_page", ["guidelines", "workout", "who"]),
        "hhs": normalize_page_bucket("hhs_guidelines", "hhs", "guidelines", "guideline_page", ["guidelines", "workout", "hhs"]),
        "acsm": normalize_page_bucket("acsm_guidelines", "acsm", "guidelines", "guideline_page", ["guidelines", "workout", "acsm"]),
        "nia": normalize_page_bucket("nia_guidelines", "nia", "guidelines", "guideline_page", ["guidelines", "workout", "older_adults", "nia"]),
        "aha": normalize_page_bucket("aha_guidelines", "aha", "guidelines", "guideline_page", ["guidelines", "workout", "cardiometabolic", "aha"]),
        "acog": normalize_page_bucket("acog_guidelines", "acog", "guidelines", "guideline_page", ["guidelines", "workout", "pregnancy", "acog"]),
        "pubmed": normalize_pubmed(),
        "pmc": normalize_pmc(),
    }
    for source, records in records_by_source.items():
        write_source_file(source, records)
    write_merged(records_by_source)


if __name__ == "__main__":
    main()
