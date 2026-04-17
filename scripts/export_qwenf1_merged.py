from __future__ import annotations
import sys
import os

# MONKEY PATCH to bypass metadata validation crash in Python 3.13
import huggingface_hub.dataclasses
def dummy_strict(cls): return cls
huggingface_hub.dataclasses.strict = dummy_strict

from unsloth import FastLanguageModel
import torch

# Config
BASE_MODEL = "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit"
ADAPTER_PATH = "outputs/qwenf1/models/qwenf1_expert_gold_v1"
MERGED_OUT = "outputs/models/EvidenceGrounded-Qwen-4B-Merged"

def main():
    print(f"Loading Base + Adapter for merging...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )
    model.load_adapter(ADAPTER_PATH)
    
    print(f"Merging and saving to Safetensors -> {MERGED_OUT}")
    # force merge for 4bit final delivery
    model.save_pretrained_merged(MERGED_OUT, tokenizer, save_method = "merged_4bit_forced")
    print("Merge & Export Complete.")

if __name__ == "__main__":
    main()
