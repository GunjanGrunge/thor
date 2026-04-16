#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
  set +a
fi

source "${ROOT_DIR}/.venv/bin/activate"
python scripts/scrape_hf_dataset.py --dataset "ishaverma/finetuning_dataset" --domain nutrition --output-name hf_nutrition --limit "${1:-500}"
python scripts/scrape_nih_ods.py --limit "${2:-80}"
python scripts/scrape_dsld.py --per-query "${3:-20}"
python scripts/scrape_pubmed_reviews.py --per-query "${4:-15}"
python scripts/scrape_guideline_pages.py
python scripts/scrape_fdc_bulk.py
python scripts/extract_fdc_bulk_wsl.py
python scripts/scrape_pmc_fulltext.py --limit "${6:-250}"

if [[ -d "${ROOT_DIR}/.venv_scrapling" ]]; then
  source "${ROOT_DIR}/.venv_scrapling/bin/activate"
  python scripts/scrape_scrapling_page_bucket.py --bucket acsm_guidelines
  python scripts/scrape_exrx_scrapling.py --limit "${5:-60}" --detail-limit "${7:-1200}"
  python scripts/scrape_musclewiki_scrapling.py --category-limit "${8:-200}" --detail-limit "${9:-1200}"
fi
