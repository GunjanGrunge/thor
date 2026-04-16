param(
    [int]$ExRxLimit = 25,
    [int]$NihLimit = 10
)

$ErrorActionPreference = "Stop"

python scripts/scrape_exrx.py --limit $ExRxLimit
python scripts/scrape_nih_ods.py --limit $NihLimit
python scripts/normalize_exrx.py
python scripts/normalize_nih_ods.py
python scripts/build_sft_seed.py
