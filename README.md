# QwenF1 Evidence Pipeline

`QwenF1` is a data-first project for building an evidence-grounded exercise physiology and sports nutrition assistant. The repository now contains both the evidence pipeline and the first real standalone fine-tuning datasets for the model.

The project currently supports:

- retrieval-augmented reasoning
- grounded synthetic coaching data generation
- supervised fine-tuning of `Qwen/Qwen3.5-4B`
- paper-quality reporting on sources, preprocessing, and evidence standards

The target assistant is intended to behave like an evidence-based exercise physiology and sports nutrition coach with screening-aware reasoning. It should ask clarifying questions, adapt recommendations to goals and constraints, explain why a recommendation is appropriate, and remain anchored to scientific and guideline evidence rather than generic fitness advice.

## Product Architecture

`QwenF1` is being built as a product stack rather than a single weight file expected to memorize everything.

The intended deployment shape is:

1. a fine-tuned consultation model
2. a retrieval layer over the scraped evidence corpus
3. a citation/product layer that can render evidence cleanly and incorporate later web updates

This means:

- fine-tuning is used to teach consultation behavior, screening, and evidence-aware reasoning style
- retrieval is used to supply factual depth, traceable evidence, and later corpus growth
- citation formatting and source presentation are handled at the product layer

The current architecture document is:

- [docs/product_architecture.md](docs/product_architecture.md)
- [docs/rag_consultation_runbook.md](docs/rag_consultation_runbook.md)
- [docs/thor_ec2_docker_runbook.md](docs/thor_ec2_docker_runbook.md)

## Research Objective

The central research question is whether a compact local model can outperform generic LLM fitness advice by combining:

- curated gold-standard nutrition databases
- structured exercise references
- scientific review literature
- clinical and public-health guideline material
- later-stage retrieval over a normalized evidence corpus

The intended product behavior is:

1. Ask about goals, injuries, medical issues, limitations, training history, and preferences.
2. Generate workout and nutrition recommendations that are explicitly constrained by those answers.
3. Back recommendations with evidence-grounded reasoning.
4. Support citation-style answers when retrieval is enabled.
5. Avoid the common failure mode of confident but weakly supported fitness guidance.

## Scope

Current scope covers four evidence layers:

- `nutrition`
  - USDA food and nutrient references
  - dietary supplement fact sheets and label data
- `workout`
  - exercise libraries and movement references
- `science`
  - review-level scientific evidence and open-access full text
- `guidelines`
  - public-health and condition-aware exercise guidance

This repository now contains:

- the raw, normalized, and chunked evidence corpus
- the embedding index used for retrieval-grounded generation
- the standalone knowledge-bearing SFT corpus
- the final first-pass training datasets for `QwenF1`

## Evidence Standard

The project prioritizes source quality over raw scale. The evidence hierarchy used here is:

### Tier 1

- `USDA FoodData Central`
- `NIH Office of Dietary Supplements`
- `Dietary Supplement Label Database (DSLD)`
- `PubMed Central (PMC)` full text when open access is available
- official public-health and professional guidance from sources such as `CDC`, `WHO`, `HHS`, `AHA`, `ACOG`, and `ACSM`

### Tier 2

- `PubMed` review and meta-analysis indexing
- `MedlinePlus`

### Tier 3

- structured exercise references such as `ExRx`
- public exercise catalogs such as `MuscleWiki`

Tier 3 sources are useful for movement coverage and exercise variation breadth, but they are not treated as the final authority for evidence-backed prescription logic.

## Current Corpus

The repository currently contains a normalized evidence corpus and a retrieval-ready chunk corpus.

### Normalized evidence counts

- `nutrition`
  - `evidence_fdc.jsonl`: `13,590`
- `supplements`
  - `evidence_nih_ods.jsonl`: `79`
  - `evidence_dsld.jsonl`: `460`
- `workout`
  - `evidence_exrx.jsonl`: `1,173`
  - `evidence_musclewiki.jsonl`: `524`
- `guidelines`
  - `evidence_cdc.jsonl`: `5`
  - `evidence_who.jsonl`: `1`
  - `evidence_hhs.jsonl`: `2`
  - `evidence_acsm.jsonl`: `1`
  - `evidence_nia.jsonl`: `1`
  - `evidence_aha.jsonl`: `3`
  - `evidence_acog.jsonl`: `1`
  - `evidence_medlineplus.jsonl`: `4`
- `science`
  - `evidence_pubmed.jsonl`: `3,295`
  - `evidence_pmc.jsonl`: `576`

### Aggregate counts

- merged normalized corpus: `19,715` records in [data/normalized/evidence_all.jsonl](data/normalized/evidence_all.jsonl)
- cleaned retrieval corpus: `19,063` records in [data/ingestion/evidence_cleaned.jsonl](data/ingestion/evidence_cleaned.jsonl)
- chunk corpus: `58,938` chunks in [data/ingestion/evidence_chunks.jsonl](data/ingestion/evidence_chunks.jsonl)
- embedding index: `58,938` vectors, `384` dimensions, built with `sentence-transformers/all-MiniLM-L6-v2`

### Coverage notes

- `USDA FoodData Central` provides the strongest nutrition breadth.
- `PubMed` and `PMC` provide the main scientific reasoning backbone.
- `ExRx` and `MuscleWiki` provide exercise breadth, movement coverage, and variation patterns.
- official guidelines provide the safety, screening, and subpopulation layer needed for condition-aware reasoning.

The corpus is now broad enough to start retrieval and grounded example generation, but it is still being expanded with a focus on exercise physiology, sports nutrition, and condition-aware prescription evidence.

## Project Docs

Additional project documentation lives in:

- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)
- [docs/AWS_UNSLOTH_TRAINING.md](docs/AWS_UNSLOTH_TRAINING.md)
- [docs/dataset.md](docs/dataset.md)
- [docs/methodology.md](docs/methodology.md)
- [docs/evaluation_plan.md](docs/evaluation_plan.md)

## Repository Layout

```text
configs/
  dsld_queries.json
  fdc_bulk_targets.json
  guideline_pages.json
  pubmed_queries.json
  sources.json

data/
  raw/
  normalized/
  ingestion/
  sft/

schemas/
  evidence_record.schema.json
  normalized_record.schema.json
  raw_record.schema.json
  sft_chat.schema.json

scripts/
  scrape_*.py
  normalize_*.py
  prepare_ingestion_corpus.py
  run_raw_collection_wsl.sh
  run_raw_growth_wsl.sh
  run_pipeline_wsl.sh
  train_qwenf1_unsloth.py
  train_qwenf1_wsl.sh
  ec2_train_download_terminate_wsl.sh
  ec2_watch_training_wsl.sh
  cleanup_training_artifacts_wsl.sh

requirements-train.txt
```

## Pipeline Stages

The pipeline is organized into explicit stages so later experiments and paper reporting can separate source acquisition from training behavior.

### 1. Raw collection

Source-specific scrapers write raw HTML, XML, JSON, or downloaded archives into `data/raw/...`.

Important collectors include:

- [scripts/scrape_fdc_bulk.py](scripts/scrape_fdc_bulk.py)
- [scripts/scrape_nih_ods.py](scripts/scrape_nih_ods.py)
- [scripts/scrape_dsld.py](scripts/scrape_dsld.py)
- [scripts/scrape_pubmed_reviews.py](scripts/scrape_pubmed_reviews.py)
- [scripts/scrape_pmc_fulltext.py](scripts/scrape_pmc_fulltext.py)
- [scripts/scrape_guideline_pages.py](scripts/scrape_guideline_pages.py)
- [scripts/scrape_exrx_scrapling.py](scripts/scrape_exrx_scrapling.py)
- [scripts/scrape_musclewiki_scrapling.py](scripts/scrape_musclewiki_scrapling.py)

### 2. Normalization

Source records are converted into a unified evidence schema in `data/normalized/`.

The main normalizer is:

- [scripts/normalize_evidence_corpus.py](scripts/normalize_evidence_corpus.py)

Each normalized record includes:

- stable ID
- domain
- source
- record type
- title and summary
- normalized content payload
- grounding URLs
- source metadata

### 3. Cleaning and chunking

The merged corpus is deduplicated, text-cleaned, and chunked for retrieval.

- [scripts/prepare_ingestion_corpus.py](scripts/prepare_ingestion_corpus.py)

Outputs:

- [data/ingestion/evidence_cleaned.jsonl](data/ingestion/evidence_cleaned.jsonl)
- [data/ingestion/evidence_chunks.jsonl](data/ingestion/evidence_chunks.jsonl)
- [data/ingestion/manifest.json](data/ingestion/manifest.json)

### 4. Embeddings and retrieval

Embedding and retrieval scripts:

- [scripts/embed_evidence_chunks.py](scripts/embed_evidence_chunks.py)
- [scripts/retrieve_evidence.py](scripts/retrieve_evidence.py)

Outputs:

- `data/embeddings/sentence-transformers__all-MiniLM-L6-v2/embeddings.npy`
- `data/embeddings/sentence-transformers__all-MiniLM-L6-v2/metadata.jsonl`
- `data/embeddings/sentence-transformers__all-MiniLM-L6-v2/manifest.json`

### 5. SFT dataset assembly

The repository now contains:

- a full-coverage standalone knowledge-bearing corpus
- grounded coaching examples curated from Bedrock generation
- final merged training files in `data/sft/final/`

Legacy broad train files:

- [data/sft/final/qwenf1_train_v1.jsonl](data/sft/final/qwenf1_train_v1.jsonl)
- [data/sft/final/qwenf1_train_v1_fullcoverage.jsonl](data/sft/final/qwenf1_train_v1_fullcoverage.jsonl)

Current strict phased train file for consultation-focused sanity-check runs:

- [data/sft/final/qwenf1_train_phase12_strict_gold.jsonl](data/sft/final/qwenf1_train_phase12_strict_gold.jsonl)

Current phase status:

- [docs/phase_training_status.md](docs/phase_training_status.md)

### 6. Unsloth training

The initial Unsloth training stack is now present:

- [scripts/train_qwenf1_unsloth.py](scripts/train_qwenf1_unsloth.py)
- [scripts/train_qwenf1_wsl.sh](scripts/train_qwenf1_wsl.sh)
- [scripts/train_qwenf1_phase12_docker.sh](scripts/train_qwenf1_phase12_docker.sh)
- [scripts/run_remote_thor_smoke_preflight_wsl.sh](scripts/run_remote_thor_smoke_preflight_wsl.sh)
- [scripts/setup_wsl_workspace.sh](scripts/setup_wsl_workspace.sh)
- [requirements-train.txt](requirements-train.txt)
- [docs/AWS_UNSLOTH_TRAINING.md](docs/AWS_UNSLOTH_TRAINING.md)
- [docs/docker_training.md](docs/docker_training.md)
- [docs/thor_ec2_docker_runbook.md](docs/thor_ec2_docker_runbook.md)

## Collection Environment

The active pipeline runs in WSL using project-local virtual environments.

### Main environment

- `.venv`
- used for requests/BeautifulSoup/XML/normalization steps

### Scrapling sidecar

- `.venv_scrapling`
- used for sources blocked to ordinary HTTP clients, especially `ExRx`, `MuscleWiki`, and some guideline pages

No global package installs are required for the intended workflow.

### Training environment

- `.venv_train`
- used for Unsloth, TRL, Transformers, and CUDA-enabled PyTorch on Linux/WSL/EC2
- preferred repeatable path going forward: Docker via [docs/docker_training.md](docs/docker_training.md)

## Quickstart

### Setup

```bash
cp .env.example .env
bash scripts/setup_wsl_env.sh
```

### Run the raw collection pipeline

```bash
bash scripts/run_raw_collection_wsl.sh
```

### Run a larger growth pass

```bash
bash scripts/run_raw_growth_wsl.sh
```

### Rebuild normalized and retrieval corpora

```bash
source .venv/bin/activate
python scripts/normalize_evidence_corpus.py
python scripts/prepare_ingestion_corpus.py
```

### Build embeddings

```bash
source .venv/bin/activate
python scripts/embed_evidence_chunks.py --batch-size 128
```

### Train QwenF1

See [docs/AWS_UNSLOTH_TRAINING.md](docs/AWS_UNSLOTH_TRAINING.md) for the full setup.

Typical Linux/WSL training flow:

```bash
cd /mnt/c/Users/Bot/Desktop/Thor
sudo bash scripts/setup_wsl_workspace.sh

cd /workspace/Thor
python3 -m venv .venv_train
source .venv_train/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
python -m pip install -r requirements-train.txt

bash scripts/train_qwenf1_wsl.sh
```

Preferred repeatable GPU flow:

```bash
docker compose -f docker-compose.unsloth.yml build
docker compose -f docker-compose.unsloth.yml run --rm thor-train bash scripts/train_qwenf1_phase12_strict_wsl.sh
```

### Run retrieval

```bash
source .venv/bin/activate
python scripts/retrieve_evidence.py --query "Create a hypertrophy workout for a beginner with mild knee pain who wants to lose fat" --top-k 5
```

## Design Principles

The project follows several constraints that matter both for engineering and for later publication.

### Evidence-first, not prompt-first

The model should not learn generic fitness style before it has access to grounded evidence. Corpus construction is treated as the primary research asset.

### Separate evidence from behavior

Raw and normalized evidence are kept separate from later supervised conversational data. This allows:

- transparent provenance
- better ablations
- later comparison between retrieval-only, SFT-only, and hybrid systems

### Prefer review-level and official guidance for reasoning

Exercise libraries are useful for movement selection and exercise variation, but higher-level reasoning should come from:

- systematic reviews
- meta-analyses
- open-access full-text reviews
- official guideline pages

### Support condition-aware screening

The intended assistant should ask about:

- goals
- injuries or pain
- disease history
- medication-relevant issues when appropriate
- recovery and tolerance constraints

The corpus therefore emphasizes exercise recommendations that can later be linked to contraindications, modification logic, and subpopulation guidance.

## Known Limitations

- Official guideline sites are often small in page count even when high in value.
- Some sources require a browser-grade fetcher and cannot be collected reliably with plain HTTP.
- Some PubMed and PMC requests fail transiently; collectors are written to fail soft and continue.
- Current corpus quality is stronger than current corpus balance; nutrition remains larger than workout-specific evidence.
- The current repository does not yet include the final grounded coaching SFT dataset.

## Intended Paper Story

This repository is being structured so it can later support a paper or technical report describing:

- source selection criteria
- evidence hierarchy
- corpus construction methodology
- normalization and provenance handling
- retrieval corpus preparation
- synthetic grounded-data generation
- model fine-tuning strategy
- evaluation against generic LLM fitness advice

The README is therefore intentionally written as both project documentation and early paper scaffolding.

## Immediate Next Step

The next phase is:

1. run the first `Qwen/Qwen3.5-4B` Unsloth training job on the balanced dataset
2. evaluate adapter behavior, safety, and factuality
3. tune hyperparameters or scale model size if needed
4. keep retrieval/web as the post-cutoff update layer
