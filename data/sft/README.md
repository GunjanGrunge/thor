# SFT Folder Guide

This folder now keeps only the datasets you are expected to use directly.

## Keep

- `qwenf1_seed_all.jsonl`
  - merged early seed dataset
- `hf_nutrition.jsonl`
  - nutrition seed rows from the Hugging Face pipeline
- `hf_workout.jsonl`
  - workout seed rows from the Hugging Face pipeline
- `supplements_seed.jsonl`
  - NIH ODS supplement seed rows
- `supplements_dsld_seed.jsonl`
  - DSLD supplement seed rows
- `grounded_examples_train_ready_bedrock_gemma3_4b_merged.jsonl`
  - current best grounded training candidates
  - this is the main file to build on for Bedrock-generated SFT data

## Archive

- `archive/`
  - contains intermediate generation inputs, validation outputs, retries, rejected rows, and older experiment files
  - safe to keep for provenance and debugging

## Current Recommended Training Input

Use:

- `grounded_examples_train_ready_bedrock_gemma3_4b_merged.jsonl`

Do not train directly from:

- raw `grounded_examples*.jsonl`
- `valid` or `invalid` files
- `curated` files unless they are explicitly marked train-ready
- generation input or failure log files
