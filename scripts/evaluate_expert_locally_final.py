from __future__ import annotations
import sys
import os
from pathlib import Path

# THE ULTIMATE MONKEY PATCH
# We must do this BEFORE importing any ML libraries
import huggingface_hub.dataclasses
def dummy_strict(cls): return cls
huggingface_hub.dataclasses.strict = dummy_strict
print("HuggingFace strict-mode validation disabled (Monkey-Patch active).")

# Now we can safely import everything
import json
import torch
from unsloth import FastLanguageModel

# Config
BASE_MODEL = "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit"
ADAPTER_PATH = "outputs/qwenf1/models/qwenf1_expert_gold_v1"
EVAL_SET = "data/eval/qwenf1_eval_expert_v1.jsonl"
OUT_DIR = "outputs/qwenf1/eval/qwenf1_expert_gold_v1"

def load_cases(path: Path):
    cases = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip(): continue
            cases.append(json.loads(line))
    return cases

def main():
    print(f"Loading Model: {BASE_MODEL}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )
    
    print(f"Loading Adapter: {ADAPTER_PATH}")
    model.load_adapter(ADAPTER_PATH)
    FastLanguageModel.for_inference(model)
    
    cases = load_cases(Path(EVAL_SET))
    os.makedirs(OUT_DIR, exist_ok=True)
    results = []
    
    print(f"Evaluating {len(cases)} expert scenarios...")
    for case in cases:
        print(f"Case: {case['id']}")
        messages = [
            {"role": "system", "content": "You are QwenF1, an expert health and performance assistant. Prioritize safety screening and medical accuracy."},
            {"role": "user", "content": case['user']}
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([prompt], return_tensors="pt").to("cuda")
        
        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
                repetition_penalty=1.05,
                pad_token_id=tokenizer.eos_token_id
            )
        
        response = tokenizer.decode(output_ids[0][inputs.input_ids.shape[-1]:], skip_special_tokens=True).strip()
        
        res = {
            "id": case['id'],
            "prompt": case['user'],
            "response": response,
        }
        results.append(res)
        
    with open(os.path.join(OUT_DIR, "eval_results_final.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"DONE. Results: {OUT_DIR}/eval_results_final.json")

if __name__ == "__main__":
    main()
