from __future__ import annotations

from pathlib import Path
import json
import os
import random

# Keep Windows/WSL fallback guards aligned with the proven Martha setup.
os.environ.setdefault("UNSLOTH_RETURN_LOGITS", "1")
os.environ.setdefault("UNSLOTH_COMPILE_DISABLE", "1")
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
os.environ.setdefault("TORCHINDUCTOR_FORCE_DISABLE_CACHES", "1")

import torch


BASE_MODEL = os.getenv(
    "UNSLOTH_BASE_MODEL",
    "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit",
)
MAX_SEQ_LENGTH = int(os.getenv("UNSLOTH_MAX_SEQ_LENGTH", "2048"))
LORA_R = int(os.getenv("UNSLOTH_LORA_R", "16"))
LORA_ALPHA = int(os.getenv("UNSLOTH_LORA_ALPHA", "32"))
LORA_DROPOUT = float(os.getenv("UNSLOTH_LORA_DROPOUT", "0.0"))
PER_DEVICE_BATCH_SIZE = int(os.getenv("UNSLOTH_BATCH_SIZE", "2"))
GRADIENT_ACCUMULATION_STEPS = int(os.getenv("UNSLOTH_GRAD_ACCUM", "8"))
MAX_STEPS = int(os.getenv("UNSLOTH_MAX_STEPS", "0"))
NUM_TRAIN_EPOCHS = float(os.getenv("UNSLOTH_NUM_EPOCHS", "2"))
LEARNING_RATE = float(os.getenv("UNSLOTH_LEARNING_RATE", "1e-5"))
LR_SCHEDULER_TYPE = os.getenv("UNSLOTH_LR_SCHEDULER", "cosine")
MIN_LEARNING_RATE = float(os.getenv("UNSLOTH_MIN_LEARNING_RATE", "0.0"))
WARMUP_STEPS = int(os.getenv("UNSLOTH_WARMUP_STEPS", "100"))
MAX_GRAD_NORM = float(os.getenv("UNSLOTH_MAX_GRAD_NORM", "1.0"))
WEIGHT_DECAY = float(os.getenv("UNSLOTH_WEIGHT_DECAY", "0.01"))
SAVE_STEPS = int(os.getenv("UNSLOTH_SAVE_STEPS", "0"))
SAVE_TOTAL_LIMIT = int(os.getenv("UNSLOTH_SAVE_TOTAL_LIMIT", "1"))
SEED = int(os.getenv("UNSLOTH_SEED", "42"))
TRAIN_DATA_PATH = os.getenv(
    "UNSLOTH_TRAIN_DATA",
    "data/sft/final/qwenf1_train_v1.jsonl",
)
TRAIN_DATA_FORMAT = os.getenv("UNSLOTH_TRAIN_FORMAT", "chat").lower()
USE_CHAT_TEMPLATE = os.getenv("UNSLOTH_USE_CHAT_TEMPLATE", "1").lower() not in {"0", "false", "no"}
OUTPUT_DIR = Path(os.getenv("UNSLOTH_OUTPUT_DIR", "outputs/qwenf1/models/qwen35_4b_lora"))

try:
    import torch._dynamo

    torch._dynamo.config.suppress_errors = True
except Exception:
    pass

random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


def require_cuda_torch() -> None:
    if "+cpu" in torch.__version__ or not torch.cuda.is_available():
        raise SystemExit(
            "CUDA PyTorch is not available in this virtual environment.\n"
            f"Detected torch version: {torch.__version__}\n"
            f"torch.version.cuda: {torch.version.cuda}\n"
            f"torch.cuda.is_available(): {torch.cuda.is_available()}\n\n"
            "Install a CUDA-enabled PyTorch build in the training environment, then rerun."
        )


require_cuda_torch()

try:
    import unsloth  # noqa: F401
    from unsloth import FastLanguageModel
except NotImplementedError as exc:
    raise SystemExit(
        "Unsloth requires an NVIDIA GPU and CUDA runtime. "
        "No supported GPU was detected in this environment."
    ) from exc

from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTTrainer

CHAT_TEMPLATE_FAILURES = 0
CHAT_TEMPLATE_FAILURE_LOG_LIMIT = 5
SKIPPED_CHAT_ROWS = 0


def format_chat(example: dict) -> str:
    global CHAT_TEMPLATE_FAILURES, SKIPPED_CHAT_ROWS
    messages = example.get("messages", [])
    normalized_messages = []
    has_user = False
    has_assistant = False
    for msg in messages:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role in {"system", "user", "assistant"}:
            normalized_messages.append({"role": role, "content": content})
            if role == "user":
                has_user = True
            elif role == "assistant":
                has_assistant = True

    if not has_user or not has_assistant:
        SKIPPED_CHAT_ROWS += 1
        return ""

    if USE_CHAT_TEMPLATE and hasattr(tokenizer, "apply_chat_template"):
        if normalized_messages:
            try:
                return tokenizer.apply_chat_template(
                    normalized_messages,
                    tokenize=False,
                    add_generation_prompt=False,
                )
            except Exception as exc:
                CHAT_TEMPLATE_FAILURES += 1
                if CHAT_TEMPLATE_FAILURES <= CHAT_TEMPLATE_FAILURE_LOG_LIMIT:
                    print(f"Falling back to plain chat formatting: {exc}")
                elif CHAT_TEMPLATE_FAILURES == CHAT_TEMPLATE_FAILURE_LOG_LIMIT + 1:
                    print(
                        "Additional chat template fallback errors suppressed; "
                        "a final count will be shown before training."
                    )

    # Keep fallback deterministic and preserve multi-turn context.
    conversation_lines = []
    for msg in normalized_messages:
        role = msg["role"].upper()
        conversation_lines.append(f"[{role}] {msg['content']}")
    return "\n".join(conversation_lines)


def load_training_texts(path: Path) -> Dataset:
    rows = []
    skipped = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                example = json.loads(line)
                if TRAIN_DATA_FORMAT != "chat":
                    raise ValueError(f"Unsupported UNSLOTH_TRAIN_FORMAT={TRAIN_DATA_FORMAT}")
                text = format_chat(example)
            except Exception as exc:
                skipped += 1
                print(f"Skipping malformed row {line_number}: {exc}")
                continue
            if text.strip():
                rows.append({"_raw_text": text})

    if not rows:
        raise RuntimeError(f"No usable training rows found in {path}")
    if skipped:
        print(f"Skipped {skipped} malformed rows.")
    return Dataset.from_list(rows)


def add_training_text(example: dict) -> dict:
    text = example["_raw_text"]
    # Qwen3.5 tokenizers may route through a processor stack where positional
    # args are interpreted as multimodal inputs. Pass text explicitly so plain
    # chat rows are never treated as image payloads.
    token_ids = tokenizer(text=text, add_special_tokens=False, truncation=False)["input_ids"]
    token_count = len(token_ids)
    max_training_tokens = max(1, MAX_SEQ_LENGTH - 2)
    was_truncated = token_count > max_training_tokens
    if was_truncated:
        text = tokenizer.decode(token_ids[:max_training_tokens], skip_special_tokens=True)
    return {
        "text": text,
        "_token_count": min(token_count, max_training_tokens),
        "_was_truncated": was_truncated,
    }


print(f"Base model: {BASE_MODEL}")
print(f"Train data: {TRAIN_DATA_PATH}")
print(f"Output dir: {OUTPUT_DIR}")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=BASE_MODEL,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=None,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    use_gradient_checkpointing="unsloth",
    random_state=SEED,
)

dataset = load_training_texts(Path(TRAIN_DATA_PATH))
dataset = dataset.map(add_training_text)
original_count = len(dataset)
truncated_count = sum(1 for item in dataset["_was_truncated"] if item)
max_training_tokens = max(1, MAX_SEQ_LENGTH - 2)
dataset = dataset.filter(lambda x: x["_token_count"] <= max_training_tokens)
kept_count = len(dataset)
if kept_count == 0:
    raise RuntimeError(
        f"No examples fit UNSLOTH_MAX_SEQ_LENGTH={MAX_SEQ_LENGTH}. "
        "Increase the sequence length or shorten the training data."
    )
dataset = dataset.remove_columns([column for column in dataset.column_names if column != "text"])
print(
    f"Training on {kept_count}/{original_count} examples "
    f"with <= {max_training_tokens} tokens before special tokens "
    f"({truncated_count} truncated)."
)
if CHAT_TEMPLATE_FAILURES:
    print(f"Chat template fallback count: {CHAT_TEMPLATE_FAILURES}")
if SKIPPED_CHAT_ROWS:
    print(f"Skipped chat rows missing user/assistant turns: {SKIPPED_CHAT_ROWS}")

training_args_kwargs = {
    "per_device_train_batch_size": PER_DEVICE_BATCH_SIZE,
    "gradient_accumulation_steps": GRADIENT_ACCUMULATION_STEPS,
    "warmup_steps": WARMUP_STEPS,
    "max_grad_norm": MAX_GRAD_NORM,
    "weight_decay": WEIGHT_DECAY,
    "max_steps": MAX_STEPS if MAX_STEPS > 0 else -1,
    "num_train_epochs": NUM_TRAIN_EPOCHS,
    "learning_rate": LEARNING_RATE,
    "fp16": not torch.cuda.is_bf16_supported(),
    "bf16": torch.cuda.is_bf16_supported(),
    "logging_steps": 20,
    "output_dir": str(OUTPUT_DIR),
    "optim": "adamw_8bit",
    "lr_scheduler_type": LR_SCHEDULER_TYPE,
    "seed": SEED,
    "data_seed": SEED,
    "report_to": "none",
}
if SAVE_STEPS > 0:
    training_args_kwargs["save_strategy"] = "steps"
    training_args_kwargs["save_steps"] = SAVE_STEPS
    if SAVE_TOTAL_LIMIT > 0:
        training_args_kwargs["save_total_limit"] = SAVE_TOTAL_LIMIT
else:
    training_args_kwargs["save_strategy"] = "no"

if LR_SCHEDULER_TYPE == "cosine_with_min_lr" and MIN_LEARNING_RATE > 0:
    training_args_kwargs["lr_scheduler_kwargs"] = {"min_lr": MIN_LEARNING_RATE}

training_args = TrainingArguments(**training_args_kwargs)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    packing=False,
    args=training_args,
)

trainer.train()
trainer.save_model(str(OUTPUT_DIR))
tokenizer.save_pretrained(str(OUTPUT_DIR))
print(f"Saved LoRA adapter to {OUTPUT_DIR}")
