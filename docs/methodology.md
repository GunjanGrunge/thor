# Methodology

This document captures the current methodological structure of the `QwenF1` evidence pipeline.

## Pipeline Overview

The workflow is:

1. raw source collection
2. source-specific preservation in `data/raw`
3. normalization to a unified evidence schema
4. cleaning and chunking for retrieval
5. embeddings and retrieval
6. grounded synthetic data generation
7. gold-QC and phased final SFT assembly
8. consultation fine-tuning plus retrieval-backed product inference

## Collection Approach

### Standard HTTP collection

Used where plain requests are reliable:

- `USDA`
- `NIH ODS`
- `DSLD`
- `PubMed`
- `PMC`
- many official guidance pages

### Browser-grade sidecar collection

Used where plain requests are blocked or unreliable:

- `ExRx`
- `MuscleWiki`
- some guideline pages such as `ACSM`

This separation is intentional. It keeps the main environment lighter while preserving access to blocked but useful sources.

## Normalization

Normalization is performed by:

- [scripts/normalize_evidence_corpus.py](../scripts/normalize_evidence_corpus.py)

The goal of normalization is to convert highly heterogeneous sources into a stable record format suitable for:

- retrieval
- filtering
- later supervised data generation

## Cleaning and Chunking

Cleaning and chunking are performed by:

- [scripts/prepare_ingestion_corpus.py](../scripts/prepare_ingestion_corpus.py)

This stage:

- removes duplicates using a source-title-summary heuristic
- cleans recurring text noise
- builds retrieval text blobs
- chunks records for later embeddings

## Methodological Principles

### Evidence-first

The repository prioritizes evidence quality before conversational style.

### Provenance preservation

Grounding URLs are retained so later retrieval and citation can trace answers to source material.

### Separation of assets

Evidence corpus and training conversations are intentionally separated.

### Fail-soft collection

Collectors are written to continue past transient failures and avoid destructive overwrites when possible.

## Grounded Example Generation

Grounded consultation examples are generated from retrieved local evidence rather than from ungrounded prompting.

Current components:

- [scripts/generate_grounded_examples.py](../scripts/generate_grounded_examples.py)
- [scripts/generate_grounded_examples_bedrock.ps1](../scripts/generate_grounded_examples_bedrock.ps1)
- [scripts/validate_grounded_examples.py](../scripts/validate_grounded_examples.py)
- [scripts/curate_grounded_examples.py](../scripts/curate_grounded_examples.py)
- [scripts/qc_gold_training_examples.py](../scripts/qc_gold_training_examples.py)
- [scripts/rewrite_gold_examples.py](../scripts/rewrite_gold_examples.py)
- [scripts/build_phased_gold_datasets.py](../scripts/build_phased_gold_datasets.py)

This stage enforces:

- evidence retrieval before generation
- JSON-structured generation outputs
- validation of evidence and screening structure
- gold-QC gating into `keep`, `needs_rewrite`, and `reject`
- phased training datasets rather than one large unfiltered SFT mix

## Product Method

The project is no longer treating fine-tuning as the only knowledge mechanism.

The intended method is:

1. fine-tune for consultation behavior
2. retrieve for evidence depth and freshness
3. render citations and source UX at the product layer

## Current Extension
The next methodological stage is:

1. continue expanding strict grounded consultation examples
2. regenerate rejected seeds where coverage is still missing
3. run low-cost phased fine-tuning on strict gold datasets only
4. evaluate the tuned model with retrieval enabled
