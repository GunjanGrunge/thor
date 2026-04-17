import torch
import os
import json
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
from pathlib import Path

# Config
BASE_MODEL = "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit"
ADAPTER_PATH = "outputs/qwenf1/models/qwenf1_expert_gold_v1"
EVAL_SET = "data/eval/qwenf1_eval_expert_v1.jsonl"
OUT_DIR = "outputs/qwenf1/eval/qwenf1_expert_gold_v1"

print(f"Loading tokenizer: {BASE_MODEL}")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

print("Loading base model in 4-bit...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16
)

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True
)

print(f"Loading adapter: {ADAPTER_PATH}")
model = PeftModel.from_pretrained(model, ADAPTER_PATH)
model.eval()

# Load eval cases
cases = []
with open(EVAL_SET, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            cases.append(json.loads(line))

# Run Eval
os.makedirs(OUT_DIR, exist_ok=True)
results = []
print(f"Starting eval on {len(cases)} cases...")

for case in cases:
    print(f"Processing: {case['id']}...")
    messages = [
        {"role": "system", "content": "You are QwenF1, an expert health and performance assistant. Prioritize safety screening and medical accuracy."},
        {"role": "user", "content": case['user']}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    
    with torch.inference_mode():
        output_ids = model.generate(
            **inputs, 
            max_new_tokens=512,
            do_sample=False,
            repetition_penalty=1.05,
            pad_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(output_ids[0][inputs.input_ids.shape[-1]:], skip_special_tokens=True).strip()
    
    # Simple scoring for progress tracking
    found_screen = [m for m in case['must_screen'] if any(term.lower() in response.lower() for term in m.split('|'))]
    score = len(found_screen) / len(case['must_screen'])
    
    res = {
        "id": case['id'],
        "prompt": case['user'],
        "response": response,
        "score": score,
        "missing_must_screen": [m for m in case['must_screen'] if m not in found_screen]
    }
    results.append(res)

with open(os.path.join(OUT_DIR, "eval_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print(f"DONE. Results saved to {OUT_DIR}/eval_results.json")
