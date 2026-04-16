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

python scripts/scrape_hf_dataset.py --dataset "padilfm/FineCorpus-WorkoutExercise" --domain workout --output-name hf_workout --limit "${1:-100}"
python scripts/scrape_hf_dataset.py --dataset "ishaverma/finetuning_dataset" --domain nutrition --output-name hf_nutrition --limit "${2:-200}"
python scripts/scrape_nih_ods.py --limit "${3:-40}"
python scripts/scrape_dsld.py --per-query "${4:-10}"
python scripts/scrape_fdc_bulk.py
python scripts/scrape_guideline_pages.py
python scripts/scrape_pubmed_reviews.py --per-query "${6:-8}"
python scripts/scrape_pmc_fulltext.py --limit "${7:-150}"

if [[ -d "${ROOT_DIR}/.venv_scrapling" ]]; then
  source "${ROOT_DIR}/.venv_scrapling/bin/activate"
  python scripts/scrape_scrapling_page_bucket.py --bucket acsm_guidelines
  python scripts/scrape_exrx_scrapling.py --limit "${8:-60}" --detail-limit "${9:-1000}"
  python scripts/scrape_musclewiki_scrapling.py --category-limit "${10:-200}" --detail-limit "${11:-1200}"
fi
