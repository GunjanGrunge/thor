from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonlines
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "configs"


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


@dataclass
class FetchResult:
    url: str
    title: str
    text: str
    html: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def load_sources() -> dict[str, Any]:
    with (CONFIG_DIR / "sources.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def fetch_page(url: str, timeout: int = 30) -> FetchResult:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else url
    text = soup.get_text("\n", strip=True)
    return FetchResult(url=url, title=title, text=text, html=response.text)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with jsonlines.open(path, mode="w") as writer:
        writer.write_all(records)


def maybe_api_key() -> str | None:
    return os.getenv("DSLD_API_KEY") or None


def maybe_env(name: str) -> str | None:
    return os.getenv(name) or None
