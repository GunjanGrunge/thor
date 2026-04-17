# Project Context

This file exists to preserve working context across sessions so future work can resume quickly without re-deriving goals, progress, or priorities.

## Project Identity

- Project name: `QwenF1`
- Core objective: build an evidence-grounded exercise physiology and sports nutrition assistant
- Base model target: `Qwen/Qwen3.5-4B`
- Intended training approach: phased consultation-focused SFT plus retrieval-backed product inference, followed by LoRA fine-tuning with Unsloth in WSL or EC2

## Product Target

The intended assistant should behave like an evidence-based:

- exercise physiology coach
- sports nutrition coach
- screening-aware reasoning system

It should not behave like a generic LLM fitness assistant that improvises unsupported advice.

Expected behavior:

1. Ask about goals.
2. Ask about injury, pain, disease, limitations, or special populations when relevant.
3. Produce workouts and nutrition plans that are adapted to those answers.
4. Explain reasoning in evidence-backed terms.
5. Support citations when retrieval is enabled.
6. Know when guidance should be modified or constrained by condition-aware evidence.

The intended product is not just a fine-tuned open model. It is:

1. a consultation-tuned model
2. plus retrieval over the evidence corpus
3. plus a citation/product layer

## Current Strategy

The project is being built in this order:

1. Build a high-quality evidence corpus.
2. Normalize all evidence into a unified schema.
3. Clean and chunk the evidence for retrieval.
4. Build embeddings and retrieval.
5. Generate grounded coaching examples from retrieved evidence.
6. Build phased strict consultation datasets.
7. Fine-tune `QwenF1` for consultation behavior.
8. Bind the tuned model to retrieval and citation/product layers.

This repository started as a corpus-construction and retrieval-preparation project.
It now also contains the first real standalone training datasets and the initial
Unsloth training stack for `QwenF1`.

## Recommended Direction

- Keep the current repo path as the primary product strategy:
  - consultation-tuned LoRA adapter training
  - local retrieval over the evidence corpus
  - evidence-backed prompt construction
  - modular inference via `qwenf1_consult_rag.py` + `qwenf1_answer_with_rag.py`
- Treat the model as behavior tuning, not the primary knowledge store.
  - retrieval should provide factual depth
  - the adapter should provide screening, validation, and consultation style
- Produce the final deployment model in a runtime-friendly format such as GGUF,
  ideally by exporting/merging the tuned adapter into a GGUF-ready base model.
- Expand sources by ingesting new web content into the same normalized evidence
  corpus and embedding index, rather than relying on live web generation.
- Reserve graph-based RAG or knowledge-graph enhancements for a later iteration
  once the core retrieval + consultation stack is stable.

## Evidence Standard

Preferred source hierarchy:

### Tier 1

- `USDA FoodData Central`
- `NIH Office of Dietary Supplements`
- `DSLD`
- `PMC` full text
- official sources such as `CDC`, `WHO`, `HHS`, `AHA`, `ACOG`, `ACSM`, `NIA`

### Tier 2

- `PubMed` review/meta-analysis indexing
- `MedlinePlus`

### Tier 3

- `ExRx`
- `MuscleWiki`

Tier 3 is allowed for movement breadth and exercise variation, but not as the main authority for reasoning or contraindication logic.

## Current Corpus State

Current normalized counts:

- `fdc`: `13,590`
- `nih_ods`: `79`
- `dsld`: `460`
- `exrx`: `1,173`
- `musclewiki`: `524`
- `cdc`: `5`
- `medlineplus`: `4`
- `who`: `1`
- `hhs`: `2`
- `acsm`: `1`
- `nia`: `1`
- `aha`: `3`
- `acog`: `1`
- `pubmed`: `3,295`
- `pmc`: `576`

Aggregate:

- merged normalized evidence: `19,715`
- cleaned retrieval corpus: `19,063`
- chunk corpus: `58,938`
- embedding index: `58,938` vectors
- embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- embedding dimensions: `384`

Important interpretation:

- nutrition breadth is strong
- workout breadth is good
- science and guideline grounding is now materially better
- corpus is sufficient to start embeddings and grounded example generation
- corpus may still be expanded further, but we are no longer blocked on evidence scale

## What Has Been Completed

- WSL local environments established
  - `.venv`
  - `.venv_scrapling`
- official source collectors implemented
- Scrapling sidecar implemented for blocked sources
- USDA bulk ingestion path implemented
- ExRx and MuscleWiki collectors implemented and expanded
- PubMed review collector implemented and expanded
- PMC full-text collector implemented
- guideline page collection expanded
- unified evidence schema in place
- normalization pipeline in place
- dedupe, cleaning, and chunking pipeline in place
- embedding and first-pass retrieval pipeline in place
- grounded coaching generation pipeline in place
- grounded example validator and curation pipeline in place
- strict gold-QC pipeline in place
- phased strict training datasets in place
- full record-to-training-row standalone corpus built
- full coverage audit completed with zero missing normalized records
- final training datasets built:
  - `data/sft/final/qwenf1_train_v1.jsonl`
  - `data/sft/final/qwenf1_train_v1_fullcoverage.jsonl`
- current strict phased training datasets built:
  - `data/sft/final/qwenf1_train_phase1_strict_gold.jsonl`
  - `data/sft/final/qwenf1_train_phase2_gold_ready.jsonl`
  - `data/sft/final/qwenf1_train_phase12_strict_gold.jsonl`
- Dockerized Thor training path added:
  - `Dockerfile.unsloth`
  - `docker-compose.unsloth.yml`
  - `scripts/run_remote_thor_smoke_preflight_wsl.sh`
  - `docs/thor_ec2_docker_runbook.md`
- AWS/WSL Unsloth training stack added:
  - `scripts/train_qwenf1_unsloth.py`
  - `scripts/train_qwenf1_wsl.sh`
  - `scripts/setup_wsl_workspace.sh`
  - `requirements-train.txt`
  - `docs/AWS_UNSLOTH_TRAINING.md`
- README rewritten as research-grade project documentation

## Important Files

High-value project files:

- [README.md](README.md)
- [datascrape.md](datascrape.md)
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)

Core configs:

- [configs/guideline_pages.json](configs/guideline_pages.json)
- [configs/pubmed_queries.json](configs/pubmed_queries.json)
- [configs/dsld_queries.json](configs/dsld_queries.json)
- [configs/fdc_bulk_targets.json](configs/fdc_bulk_targets.json)

Core scripts:

- [scripts/scrape_fdc_bulk.py](scripts/scrape_fdc_bulk.py)
- [scripts/scrape_nih_ods.py](scripts/scrape_nih_ods.py)
- [scripts/scrape_dsld.py](scripts/scrape_dsld.py)
- [scripts/scrape_pubmed_reviews.py](scripts/scrape_pubmed_reviews.py)
- [scripts/scrape_pmc_fulltext.py](scripts/scrape_pmc_fulltext.py)
- [scripts/scrape_guideline_pages.py](scripts/scrape_guideline_pages.py)
- [scripts/scrape_exrx_scrapling.py](scripts/scrape_exrx_scrapling.py)
- [scripts/scrape_musclewiki_scrapling.py](scripts/scrape_musclewiki_scrapling.py)
- [scripts/normalize_evidence_corpus.py](scripts/normalize_evidence_corpus.py)
- [scripts/prepare_ingestion_corpus.py](scripts/prepare_ingestion_corpus.py)
- [scripts/embed_evidence_chunks.py](scripts/embed_evidence_chunks.py)
- [scripts/retrieve_evidence.py](scripts/retrieve_evidence.py)

Core outputs:

- [data/normalized/evidence_all.jsonl](data/normalized/evidence_all.jsonl)
- [data/ingestion/evidence_cleaned.jsonl](data/ingestion/evidence_cleaned.jsonl)
- [data/ingestion/evidence_chunks.jsonl](data/ingestion/evidence_chunks.jsonl)
- [data/ingestion/manifest.json](data/ingestion/manifest.json)
- [data/embeddings/sentence-transformers__all-MiniLM-L6-v2/manifest.json](data/embeddings/sentence-transformers__all-MiniLM-L6-v2/manifest.json)
- [data/sft/final/qwenf1_train_v1.jsonl](data/sft/final/qwenf1_train_v1.jsonl)
- [data/sft/final/qwenf1_train_v1_fullcoverage.jsonl](data/sft/final/qwenf1_train_v1_fullcoverage.jsonl)

Training files:

- [scripts/train_qwenf1_unsloth.py](scripts/train_qwenf1_unsloth.py)
- [scripts/train_qwenf1_wsl.sh](scripts/train_qwenf1_wsl.sh)
- [scripts/setup_wsl_workspace.sh](scripts/setup_wsl_workspace.sh)
- [requirements-train.txt](requirements-train.txt)
- [docs/AWS_UNSLOTH_TRAINING.md](docs/AWS_UNSLOTH_TRAINING.md)

## Current Constraints

- Avoid Windows global installs.
- Use WSL-local project environments.
- Keep evidence separate from later SFT data.
- Preserve provenance and grounding URLs.
- Prefer fail-soft collection so transient network issues do not destroy existing data.

## Current Training State

Final dataset counts:

- balanced training set: `9,303`
- full-coverage training set: `19,764`
- full normalized-record coverage in standalone corpus: `19,715 / 19,715`

Balanced domain mix:

- `nutrition`: `4,020`
- `science`: `3,000`
- `workout`: `1,706`
- `supplements`: `556`
- `guidelines`: `18`
- `combined`: `3`

Current strict phased consultation set:

- `qwenf1_train_phase12_strict_gold.jsonl`: `39`
- domain mix:
  - `combined`: `12`
  - `workout`: `12`
  - `nutrition`: `10`
  - `supplements`: `5`

Interpretation:

- broad legacy files still exist for research/reference purposes
- the next paid training runs should not use those broad files directly
- the next low-cost sanity-check run should use the strict phased consultation file

## Known Gaps

- Evaluation framework is not yet implemented.
- Training has not been run yet on the new Thor stack.
- The previous EC2 Docker smoke run failed against a stale image with missing
  `Python.h`. The guarded rebuild/validate path now exists, but it has not yet
  been re-verified on a fresh instance in this session.
- Nutrition still outweighs workout in raw corpus size and in the balanced SFT mix.
- Some official sites are inherently low-count but high-value.

## Immediate Next Step

The next implementation step should be:

1. keep expanding strict grounded consultation rows
2. regenerate the remaining rejected workout seeds
3. run a low-cost sanity-check fine-tune on `qwenf1_train_phase12_strict_gold.jsonl`
4. evaluate the tuned model together with retrieval instead of treating fine-tuning as the only knowledge mechanism

## Reminder For Future Sessions

When resuming work:

1. read `README.md`
2. read `PROJECT_CONTEXT.md`
3. check `data/normalized/evidence_manifest.jsonl`
4. check `data/ingestion/manifest.json`
5. check `docs/phase_training_status.md`
6. continue from phased strict training and retrieval-backed product work unless the user explicitly wants more source expansion
