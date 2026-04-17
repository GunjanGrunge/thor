from __future__ import annotations
import sys
import os

# MONKEY PATCH to bypass metadata validation crash in Python 3.13
import huggingface_hub.dataclasses
def dummy_strict(cls): return cls
huggingface_hub.dataclasses.strict = dummy_strict

from unsloth import FastLanguageModel

# Config
BASE_MODEL = "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit"
ADAPTER_PATH = "outputs/qwenf1/models/qwenf1_expert_gold_v1"
GGUF_OUT = "outputs/qwenf1/models/qwenf1_expert_gold_v1_gguf"

def main():
    print(f"Loading Base + Adapter for GGUF export...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )
    model.load_adapter(ADAPTER_PATH)
    
    print(f"Exporting to GGUF (q4_k_m) -> {GGUF_OUT}")
    # This merges the LoRA adapter into the base model and saves as GGUF
    model.save_pretrained_gguf(
        GGUF_OUT, 
        tokenizer, 
        quantization_method = "q4_k_m"
    )
    print("Export Complete.")

if __name__ == "__main__":
    main()
