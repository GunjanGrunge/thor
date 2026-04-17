from __future__ import annotations

import os
import sys
import importlib.machinery
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import numpy as np
import torch

if os.environ.get("THOR_DISABLE_HF_KERNELS", "1") == "1" and "kernels" not in sys.modules:
    stub = ModuleType("kernels")
    stub.__spec__ = importlib.machinery.ModuleSpec("kernels", loader=None)
    sys.modules["kernels"] = stub

from transformers import AutoModel, AutoTokenizer


def maybe_set_windows_hf_cache() -> None:
    candidates = [
        Path(r"C:\Users\Bot\.cache\huggingface"),
        Path("/mnt/c/Users/Bot/.cache/huggingface"),
    ]
    for candidate in candidates:
        if candidate.exists() and "HF_HOME" not in os.environ:
            os.environ["HF_HOME"] = str(candidate)
            break


def sanitize_model_name(model_name: str) -> str:
    return model_name.replace("/", "__")


def has_local_model_snapshot(model_name: str) -> bool:
    hf_home = os.environ.get("HF_HOME", "")
    if not hf_home:
        return False
    hub_dir = Path(hf_home) / "hub"
    repo_dir = hub_dir / f"models--{model_name.replace('/', '--')}"
    snapshots_dir = repo_dir / "snapshots"
    return snapshots_dir.exists() and any(snapshots_dir.iterdir())


def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1),
        min=1e-9,
    )


@lru_cache(maxsize=4)
def load_embed_stack(model_name: str):
    maybe_set_windows_hf_cache()
    local_files_only = has_local_model_snapshot(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModel.from_pretrained(model_name, local_files_only=local_files_only)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()
    return tokenizer, model, device


def encode_texts(texts: list[str], model_name: str) -> np.ndarray:
    tokenizer, model, device = load_embed_stack(model_name)
    encoded_input = tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(device)
    with torch.no_grad():
        model_output = model(**encoded_input)
    sentence_embeddings = mean_pooling(model_output, encoded_input["attention_mask"])
    sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
    return sentence_embeddings.cpu().numpy().astype(np.float32)
