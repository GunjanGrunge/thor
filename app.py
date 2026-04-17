import os
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

# Local Imports
import sys
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.retrieve_evidence import retrieve_evidence

app = FastAPI(title="Evidence-Grounded Health AI API")

# Setup Constants
MODEL_PATH = "outputs/models/EvidenceGrounded-Qwen-4B-Merged"
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    stream: Optional[bool] = False

class Evidence(BaseModel):
    id: str
    text: str
    score: float
    source: str

class QueryResponse(BaseModel):
    query: str
    answer: str
    evidence: List[Evidence]

@app.get("/health")
def health_check():
    return {"status": "healthy", "model": "EvidenceGrounded-Qwen-4B"}

@app.post("/ask", response_model=QueryResponse)
async def ask(request: QueryRequest):
    # 1. Retrieve Evidence
    try:
        raw_evidence = retrieve_evidence(request.query, top_k=request.top_k)
        evidence_list = [
            Evidence(
                id=item["id"],
                text=item["text"],
                score=item["score"],
                source=item.get("metadata", {}).get("source", "Unknown")
            ) for item in raw_evidence
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")

    # 2. Build Context-Aware Prompt
    evidence_text = "\n".join([f"- {e.text}" for e in evidence_list])
    prompt = f"""You are an Expert Health Assistant. Use the following retrieved evidence to answer the user query accurately. 
If the evidence is insufficient, use your expert training to provide safety screening questions.

RELEVANT EVIDENCE:
{evidence_text}

USER QUERY:
{request.query}

EXPERT RESPONSE:"""

    # 3. Call Inference (Ollama as zero-cost low-latency backend)
    # This is a placeholder for where the user can choose Ollama or local Llama-cpp
    import requests
    try:
        payload = {
            "model": "qwen3-expert", # User should create this model in Ollama via Modelfile
            "prompt": prompt,
            "stream": False
        }
        res = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        if res.status_code == 200:
            answer = res.json().get("response", "No response generated.")
        else:
            answer = f"Error: Ollama backend reached but failed with code {res.status_code}. (Note: Ensure 'qwen3-expert' model is created in Ollama)."
    except Exception as e:
        answer = f"Ollama connection error: {str(e)}. Please ensure Ollama is running at {OLLAMA_API_URL}."

    return QueryResponse(
        query=request.query,
        answer=answer,
        evidence=evidence_list
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
