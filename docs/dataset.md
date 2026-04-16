# Dataset Notes

This document is the paper-oriented reference for the evidence corpus that underpins `QwenF1`.

## Purpose

The corpus is being assembled to support:

- retrieval-augmented evidence access
- grounded synthetic training example generation
- final supervised fine-tuning
- reporting of corpus provenance and quality

## Corpus Layers

The corpus has four major layers:

- nutrition references
- workout and exercise references
- supplement evidence
- scientific and guideline evidence

## Primary Sources

### Nutrition

- `USDA FoodData Central`

### Supplements

- `NIH ODS`
- `DSLD`

### Scientific evidence

- `PubMed`
- `PMC`

### Exercise and workout references

- `ExRx`
- `MuscleWiki`

### Official guidance

- `CDC`
- `WHO`
- `HHS`
- `AHA`
- `ACOG`
- `ACSM`
- `NIA`
- `MedlinePlus`

## Current Quantitative Snapshot

Current normalized counts:

- `evidence_fdc.jsonl`: `13,590`
- `evidence_nih_ods.jsonl`: `79`
- `evidence_dsld.jsonl`: `460`
- `evidence_exrx.jsonl`: `1,173`
- `evidence_musclewiki.jsonl`: `524`
- `evidence_pubmed.jsonl`: `3,295`
- `evidence_pmc.jsonl`: `576`
- guideline/support pages across official sources: `18`

Aggregate:

- `evidence_all.jsonl`: `19,715`
- `evidence_cleaned.jsonl`: `19,063`
- `evidence_chunks.jsonl`: `58,938`

## Schema

The unified evidence schema is defined in:

- [schemas/evidence_record.schema.json](../schemas/evidence_record.schema.json)

Common fields include:

- `id`
- `domain`
- `source`
- `record_type`
- `title`
- `summary`
- `content`
- `tags`
- `grounding_urls`
- `metadata`

## Intended Downstream Use

The evidence corpus is not the final SFT dataset. It is a grounding asset that will later be used to:

1. retrieve relevant evidence chunks
2. synthesize grounded coaching interactions
3. preserve citation provenance
4. construct a filtered supervised dataset

That next step is already underway in this repository. The current training policy is phased:

- broad legacy SFT files are preserved for research/reference
- strict gold-QC consultation files are used for the next paid fine-tuning runs

Current strict phased train file:

- [../data/sft/final/qwenf1_train_phase12_strict_gold.jsonl](../data/sft/final/qwenf1_train_phase12_strict_gold.jsonl)

Current phase status:

- [phase_training_status.md](phase_training_status.md)

## Paper Relevance

This corpus design supports later reporting on:

- source selection
- evidence hierarchy
- corpus balance
- normalization methodology
- provenance retention
- retrieval-preparation strategy
