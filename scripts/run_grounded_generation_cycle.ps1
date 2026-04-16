param(
  [int]$TopK = 6,
  [string]$EmbeddingModel = "sentence-transformers/all-MiniLM-L6-v2",
  [string]$GenerationModel = "qwen3:8b",
  [string]$ProjectRoot = "C:\Users\Bot\Desktop\Thor"
)

$ErrorActionPreference = "Stop"

$wslProjectRoot = "/mnt/c/Users/Bot/Desktop/Thor"

Write-Host "[1/4] preparing grounded prompts in WSL"
wsl bash -lc "cd $wslProjectRoot && source .venv/bin/activate && python scripts/generate_grounded_examples.py --prepare-only --embed-model '$EmbeddingModel' --gen-model '$GenerationModel' --top-k $TopK"

Write-Host "[2/4] generating grounded examples with local Ollama"
& "$ProjectRoot\scripts\generate_grounded_examples_ollama.ps1"

Write-Host "[3/5] validating generated examples in WSL"
wsl bash -lc "cd $wslProjectRoot && source .venv/bin/activate && python scripts/validate_grounded_examples.py"

Write-Host "[4/5] curating train-ready grounded examples in WSL"
wsl bash -lc "cd $wslProjectRoot && source .venv/bin/activate && python scripts/curate_grounded_examples.py"

Write-Host "[5/5] printing project summary"
wsl bash -lc "cd $wslProjectRoot && source .venv/bin/activate && python scripts/project_status_summary.py"
