# Retrieval-Backed Consultation Runbook

This runbook describes the intended inference path for the `QwenF1` product stack.

## Purpose

The goal is to combine:

- a consultation-tuned `QwenF1` model
- local retrieval over the evidence corpus
- later citation/product rendering

This avoids forcing the model to memorize the whole corpus while still keeping behavior specialized.

## Current Script

- `scripts/qwenf1_consult_rag.py`

This script:

1. accepts a user query
2. optionally accepts a structured profile JSON
3. retrieves top evidence chunks from the local embedding index
4. builds the model-facing consultation messages
5. emits a JSON payload that can be fed to a local inference runtime or product API layer

## Example

```bash
python scripts/qwenf1_consult_rag.py \
  --query "I have high blood pressure and knee pain but want to lose fat and get stronger. Where should I start?" \
  --profile-json configs/sample_consult_profile.json \
  --top-k 6 \
  --output outputs/qwenf1/consultation_example.json
```

## Output Shape

The output includes:

- `system_prompt`
- `query`
- `profile`
- `retrieved_evidence`
- `messages`

The `messages` field is the model-facing conversation payload.

## Intended Product Flow

1. user asks a consultation question
2. product layer gathers known profile details
3. retrieval layer fetches evidence chunks
4. the consultation model receives:
   - system prompt
   - user request
   - profile context
   - retrieved evidence
5. model answers with screening-aware reasoning
6. product layer later maps citations to displayed sources

## Important Constraint

This script does not itself run the model.

That is intentional.

It separates:

- retrieval and prompt construction
- from inference runtime and product UX

This keeps the system modular so the same retrieval layer can be used with:

- local adapter inference
- future API inference
- future tool/citation rendering layers

## End-to-End Local Inference

To run the local adapter on top of the retrieval-built payload, use:

- `scripts/qwenf1_answer_with_rag.py`

Example using the saved consultation payload:

```bash
python scripts/qwenf1_answer_with_rag.py \
  --payload-json outputs/qwenf1/consultation_example.json \
  --adapter outputs/qwenf1/models/qwen3_4b_instruct2507_lora_v1 \
  --output outputs/qwenf1/consultation_answer.json
```

Or generate retrieval plus answer in one command:

```bash
python scripts/qwenf1_answer_with_rag.py \
  --query "I have high blood pressure and knee pain but want to lose fat and get stronger. Where should I start?" \
  --profile-json configs/sample_consult_profile.json \
  --top-k 6 \
  --adapter outputs/qwenf1/models/qwen3_4b_instruct2507_lora_v1 \
  --output outputs/qwenf1/consultation_answer.json
```
