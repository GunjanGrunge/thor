import os
import json
import time
from pathlib import Path
import jsonlines
import numpy as np
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INGEST_DIR = DATA_DIR / "ingestion"
EMBED_DIR = DATA_DIR / "embeddings"

def load_dotenv():
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

load_dotenv()
API_KEY = os.environ.get("NVIDIA_API_KEY")
BASE_URL = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL_NAME = "nvidia/nv-embedqa-e5-v5"

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def sanitize_model_name(model_name: str) -> str:
    return model_name.replace("/", "__")

def load_chunks(path: Path, limit: int | None = None) -> list[dict]:
    records = []
    with jsonlines.open(path, mode="r") as reader:
        for record in reader:
            records.append(record)
            if limit is not None and len(records) >= limit:
                break
    return records

def get_nvidia_embeddings(texts: list[str]) -> list[list[float]]:
    try:
        res = requests.post(
            f"{BASE_URL}/embeddings",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL_NAME,
                "input": texts,
                "input_type": "passage",
                "encoding_format": "float",
                "truncate": "END"
            },
            timeout=60
        )
        res.raise_for_status()
        data = res.json()
        return [item["embedding"] for item in data["data"]]
    except Exception as e:
        print(f"Error fetching embeddings: {e}")
        if hasattr(e, 'response') and e.response: # type: ignore
            print(e.response.text) # type: ignore
        raise

def main():
    if not API_KEY:
        raise ValueError("NVIDIA_API_KEY not set")

    parser = __import__('argparse').ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=100, help="Chunks to send per request")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    input_path = INGEST_DIR / "evidence_chunks.jsonl"
    records = load_chunks(input_path, args.limit)
    texts = [record["text"] for record in records]
    
    print(f"Encoding {len(texts)} chunks using {MODEL_NAME} via NVIDIA NIM...")
    all_embeddings = []
    
    for i in range(0, len(texts), args.batch_size):
        batch = texts[i : i + args.batch_size]
        print(f"Processing batch {i} to {i + len(batch)}...")
        
        # Exponential backoff for rate limits
        retries = 3
        while retries > 0:
            try:
                embeddings = get_nvidia_embeddings(batch)
                all_embeddings.extend(embeddings)
                break
            except Exception as e:
                retries -= 1
                if retries == 0:
                    raise
                print("Rate limited or error, sleeping 5s...")
                time.sleep(5)
        
        # Friendly rate limit pause (NVIDIA allows 40 RPM, we process conservatively)
        time.sleep(1.5)

    embeddings_np = np.vstack(all_embeddings).astype(np.float32)

    # Normalize the embeddings for cosine similarity
    normals = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
    embeddings_np = embeddings_np / np.clip(normals, 1e-9, None)

    out_dir = EMBED_DIR / sanitize_model_name(MODEL_NAME)
    ensure_dir(out_dir)

    metadata_path = out_dir / "metadata.jsonl"
    embeddings_path = out_dir / "embeddings.npy"
    manifest_path = out_dir / "manifest.json"

    with jsonlines.open(metadata_path, mode="w") as writer:
        writer.write_all(records)

    np.save(embeddings_path, embeddings_np)

    manifest = {
        "model": MODEL_NAME,
        "input_path": str(input_path),
        "metadata_path": str(metadata_path),
        "embeddings_path": str(embeddings_path),
        "records": len(records),
        "dimensions": int(embeddings_np.shape[1]) if len(records) else 0,
        "normalized": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print("\nSuccessfully updated the RAG vector store!")

if __name__ == "__main__":
    main()
