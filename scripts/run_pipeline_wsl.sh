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

python scripts/scrape_hf_dataset.py --dataset "padilfm/FineCorpus-WorkoutExercise" --domain workout --output-name hf_workout --limit "${1:-25}"
python scripts/scrape_hf_dataset.py --dataset "ishaverma/finetuning_dataset" --domain nutrition --output-name hf_nutrition --limit "${2:-25}"
python scripts/scrape_nih_ods.py --limit "${3:-10}"
python scripts/scrape_dsld.py --per-query "${4:-5}"
python scripts/normalize_hf_chat.py --input-name hf_workout --domain workout
python scripts/normalize_hf_chat.py --input-name hf_nutrition --domain nutrition
python scripts/normalize_nih_ods.py
python scripts/normalize_dsld.py
python scripts/build_sft_seed.py
