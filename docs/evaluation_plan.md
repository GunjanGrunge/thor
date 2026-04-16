# Evaluation Plan

This file is an early scaffold for the later evaluation section of a paper or technical report.

## Goal

Evaluate whether `QwenF1` can outperform generic LLM fitness responses by producing:

- more evidence-grounded recommendations
- better screening behavior
- safer handling of constraints and conditions
- more specific and supportable reasoning

## Evaluation Themes

### 1. Screening quality

Test whether the assistant asks for:

- goals
- injuries or pain
- disease history
- training background
- practical constraints

### 2. Evidence grounding

Test whether recommendations can be traced to:

- guideline pages
- systematic reviews
- full-text review evidence
- nutrition databases

### 3. Recommendation quality

Test whether output quality improves on:

- exercise selection
- progression logic
- nutrition support
- subpopulation adaptation
- contraindication awareness

### 4. Citation support

Once retrieval is enabled, test whether the assistant can:

- cite relevant evidence
- remain consistent with retrieved material
- avoid fabricating citations

## Candidate Benchmark Categories

- hypertrophy programming
- fat-loss programming
- beginner general health training
- older adult exercise
- pregnancy/postpartum exercise
- hypertension-aware exercise advice
- diabetes-aware exercise advice
- low back pain modification logic
- protein and calorie planning
- supplement reasoning with safety caveats

## Candidate Comparators

- generic LLM without retrieval
- generic LLM with no domain-specific dataset
- retrieval-only baseline
- `QwenF1` with retrieval
- `QwenF1` after grounded SFT

## Metrics To Add Later

- screening completeness
- evidence citation correctness
- contraindication sensitivity
- recommendation specificity
- hallucination rate
- reviewer preference ranking

## Note

This evaluation plan is not yet implemented. It is included now so the repository and README can support future paper writing without needing to reconstruct the intended benchmarks later.

## Implemented First Pass

The repository now includes a first-pass adapter evaluation flow for post-training checks:

- eval set: `data/eval/qwenf1_eval_v1.jsonl`
- evaluator: `scripts/evaluate_qwenf1_adapter.py`
- WSL wrapper: `scripts/evaluate_qwenf1_wsl.sh`

This first pass is heuristic, not a full paper-grade benchmark. It is intended to answer:

- does the adapter ask the right screening questions?
- does it avoid obvious unsafe shortcuts?
- does it include expected directionally correct content?

Outputs are written under:

- `outputs/qwenf1/eval/.../qwenf1_eval_results.json`
- `outputs/qwenf1/eval/.../qwenf1_eval_summary.json`
- `outputs/qwenf1/eval/.../qwenf1_eval_report.md`

This should be treated as a smoke evaluation layer before larger human review or retrieval-grounded benchmarking.
