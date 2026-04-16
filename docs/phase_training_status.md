# QwenF1 Phase Training Status

Current strict dataset:
- `data/sft/final/qwenf1_train_phase12_strict_gold.jsonl`
- Examples: `39`
- Domain coverage:
  - `combined`: `12`
  - `workout`: `12`
  - `nutrition`: `10`
  - `supplements`: `5`

Use this dataset only for a low-cost phased sanity-check run.
Do not use the older broad files for the next paid EC2 training run:
- `data/sft/final/qwenf1_train_v1.jsonl`
- `data/sft/final/qwenf1_train_v1_fullcoverage.jsonl`

Recommended WSL/EC2 entrypoint for the strict phased run:
- `bash scripts/train_qwenf1_phase12_strict_wsl.sh`

Remaining regeneration queue:
- `seed_tendinopathy_return_v3`
- `seed_triathlon_strength_v3`

Regeneration seed config:
- `configs/grounded_generation_seeds_phase3_regen.json`
