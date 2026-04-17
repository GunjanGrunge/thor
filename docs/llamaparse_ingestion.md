# LlamaParse Ingestion

Thor can run a separate LlamaParse enrichment pass over raw source files without changing the existing normalization and training pipeline.

## Supported source buckets

- `exrx`
- `nih_ods`
- `pmc`
- `musclewiki`

The parser reads the existing raw sidecar JSON files and follows `html_path`, `xml_path`, `pdf_path`, or `file_path` entries to the underlying document.

## Environment

Set one or more API keys in `.env`:

```bash
LLAMA_CLOUD_API_KEY_1=replace_me
LLAMA_CLOUD_API_KEY_2=replace_me
```

The parser rotates keys in round-robin order and enforces a per-run request budget for each key.

## Install

```bash
pip install -r requirements.txt
```

## Example

Parse 50 ExRx files into `data/parsed/llamaparse`:

```bash
python scripts/parse_visual_evidence_llamaparse.py --source exrx --limit 50
```

Parse NIH ODS and PMC with explicit text output:

```bash
python scripts/parse_visual_evidence_llamaparse.py --source nih_ods --source pmc --result-type text
```

## Outputs

- Per-document JSON artifacts under `data/parsed/llamaparse/<source>/`
- Append-only run manifest at `data/parsed/llamaparse/manifest.jsonl`
- Last run rollup at `data/parsed/llamaparse/last_run_summary.json`
