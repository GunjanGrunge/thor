param(
  [int]$TopK = 6,
  [int]$Limit = 20,
  [string]$EmbeddingModel = "sentence-transformers/all-MiniLM-L6-v2",
  [string]$GenerationModel = "google.gemma-3-4b-it",
  [string]$Region = "us-east-1",
  [string]$ProjectRoot = "C:\Users\Bot\Desktop\Thor",
  [string]$Tag = "bedrock_gemma3_4b_v2",
  [string]$SeedConfig = "configs/grounded_generation_seeds_v2.json",
  [switch]$BuildBehaviorDataset,
  [switch]$RunGoldQc
)

$ErrorActionPreference = "Stop"

$wslProjectRoot = "/mnt/c/Users/Bot/Desktop/Thor"
$promptOutput = Join-Path $ProjectRoot ("data\sft\grounded_generation_inputs_" + $Tag + ".jsonl")
$generatedOutput = Join-Path $ProjectRoot ("data\sft\grounded_examples_" + $Tag + ".jsonl")
$failureOutput = Join-Path $ProjectRoot ("data\sft\grounded_generation_failures_" + $Tag + ".jsonl")
$validationReport = "data/sft/grounded_examples_validation_" + $Tag + ".json"
$validOutput = "data/sft/grounded_examples_valid_" + $Tag + ".jsonl"
$invalidOutput = "data/sft/grounded_examples_invalid_" + $Tag + ".jsonl"
$curatedOutput = "data/sft/grounded_examples_curated_" + $Tag + ".jsonl"
$trainOutput = "data/sft/grounded_examples_train_ready_" + $Tag + ".jsonl"
$rejectedOutput = "data/sft/grounded_examples_rejected_" + $Tag + ".jsonl"
$curationReport = "data/sft/grounded_examples_curation_report_" + $Tag + ".json"
$qcReport = "outputs/qwenf1/gold_qc/" + $Tag + "_report.json"
$qcKeep = "outputs/qwenf1/gold_qc/" + $Tag + "_keep.jsonl"
$qcRewrite = "outputs/qwenf1/gold_qc/" + $Tag + "_needs_rewrite.jsonl"
$qcReject = "outputs/qwenf1/gold_qc/" + $Tag + "_reject.jsonl"
$qcGold = "data/sft/final/qwenf1_train_v2_gold_candidate.jsonl"

Write-Host "[1/4] preparing grounded prompts in WSL"
wsl bash -lc "cd $wslProjectRoot && source .venv/bin/activate && python scripts/generate_grounded_examples.py --prepare-only --seed-config '$SeedConfig' --embed-model '$EmbeddingModel' --gen-model '$GenerationModel' --top-k $TopK --limit $Limit --prompt-output 'data/sft/grounded_generation_inputs_$Tag.jsonl'"

Write-Host "[2/4] generating grounded examples with AWS Bedrock"
& "$ProjectRoot\scripts\generate_grounded_examples_bedrock.ps1" -InputPath $promptOutput -OutputPath $generatedOutput -FailurePath $failureOutput -ModelId $GenerationModel -Region $Region

Write-Host "[3/4] validating generated examples in WSL"
wsl bash -lc "cd $wslProjectRoot && source .venv/bin/activate && python scripts/validate_grounded_examples.py --input 'data/sft/grounded_examples_$Tag.jsonl' --report '$validationReport' --valid-output '$validOutput' --invalid-output '$invalidOutput'"

Write-Host "[4/4] curating train-ready examples in WSL"
wsl bash -lc "cd $wslProjectRoot && source .venv/bin/activate && python scripts/curate_grounded_examples.py --input 'data/sft/grounded_examples_$Tag.jsonl' --curated-output '$curatedOutput' --train-output '$trainOutput' --rejected-output '$rejectedOutput' --report '$curationReport'"

if ($BuildBehaviorDataset) {
  Write-Host "[5/5] building behavior-only final dataset in WSL"
  wsl bash -lc "cd $wslProjectRoot && source .venv/bin/activate && python scripts/build_behavior_training_dataset.py --grounded-input '$trainOutput' --output 'data/sft/final/qwenf1_train_v2_behavior.jsonl' --manifest 'data/sft/final/qwenf1_train_v2_behavior_manifest.json'"
}

if ($RunGoldQc) {
  Write-Host "[6/6] running gold-standard QC in WSL"
  wsl bash -lc "cd $wslProjectRoot && source .venv/bin/activate && python scripts/qc_gold_training_examples.py --input 'data/sft/grounded_examples_$Tag.jsonl' --report '$qcReport' --keep-output '$qcKeep' --rewrite-output '$qcRewrite' --reject-output '$qcReject' --gold-output '$qcGold'"
}
