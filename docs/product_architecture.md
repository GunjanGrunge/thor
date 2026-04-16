# Product Architecture

`QwenF1` should be built as a product system, not as a single fine-tuned weight file expected to memorize the entire corpus.

## Core Design

The intended production architecture has three layers:

1. `consultation model`
2. `evidence retrieval layer`
3. `citation and product interface layer`

## 1. Consultation Model

The fine-tuned model is responsible for:

- asking the right screening questions
- adapting advice to goals, injuries, disease state, and constraints
- using cautious, evidence-aware reasoning
- giving provisional next steps when important details are missing
- avoiding generic unsupported fitness advice

The fine-tune should emphasize:

- consultation behavior
- screening logic
- constraint-aware planning
- tone and safety
- evidence-aware reasoning style

The fine-tune should not be expected to carry the whole evidence corpus by memorization alone.

## 2. Evidence Retrieval Layer

The retrieval layer is responsible for:

- surfacing relevant scientific and guideline evidence
- expanding detail beyond what is in the fine-tuned weights
- preserving traceability to authentic sources
- reducing hallucination on factual claims
- enabling corpus growth without retraining the consultation model every time

Current retrieval assets already present in the repository:

- cleaned evidence corpus
- chunked retrieval corpus
- embedding index
- retrieval script

Primary files:

- `data/ingestion/evidence_cleaned.jsonl`
- `data/ingestion/evidence_chunks.jsonl`
- `data/embeddings/sentence-transformers__all-MiniLM-L6-v2/embeddings.npy`
- `data/embeddings/sentence-transformers__all-MiniLM-L6-v2/metadata.jsonl`
- `scripts/retrieve_evidence.py`

## 3. Citation and Product Interface Layer

The final product layer is responsible for:

- rendering citations in a user-friendly format
- mapping inline citation references to source metadata
- optionally showing superscript references or expandable source cards
- optionally calling external tools or live retrieval for updated evidence
- enforcing UX and policy constraints beyond the model itself

This layer is the right place to implement:

- superscript citation formatting
- clickable evidence cards
- live source refresh
- web updates beyond corpus cutoff

## Why This Split Is Correct

If all knowledge is forced into fine-tuning:

- retraining becomes expensive and repetitive
- new data requires another training cycle
- stale facts persist in the model
- the product becomes harder to maintain

If the model is only prompted without fine-tuning:

- consultation behavior is inconsistent
- safety and screening quality are weak
- the model behaves like a generic assistant

The correct product design is therefore:

- fine-tune for consultation behavior
- retrieve for evidence depth and freshness
- render citations and tools at the product layer

## Current Training Policy

For the next paid training runs, use only phased strict datasets that passed gold QC.

Current strict train file:

- `data/sft/final/qwenf1_train_phase12_strict_gold.jsonl`

This file is suitable for:

- low-cost sanity-check fine-tuning
- behavior verification
- early product binding tests with retrieval

It is not yet the final large-scale production SFT set.

## Near-Term Build Order

1. continue expanding strict grounded consultation examples
2. keep retrieval corpus and embeddings current
3. run phased consultation fine-tunes only on strict gold datasets
4. evaluate the tuned model with retrieval enabled
5. build citation rendering and product orchestration on top
