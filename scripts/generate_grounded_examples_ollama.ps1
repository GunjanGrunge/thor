param(
  [string]$InputPath = "",
  [string]$OutputPath = "",
  [string]$FailurePath = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$inputPath = if ($InputPath) { $InputPath } else { Join-Path $root "data\sft\grounded_generation_inputs.jsonl" }
$outputPath = if ($OutputPath) { $OutputPath } else { Join-Path $root "data\sft\grounded_examples.jsonl" }
$failurePath = if ($FailurePath) { $FailurePath } else { Join-Path $root "data\sft\grounded_generation_failures.jsonl" }
$ollamaUrl = "http://127.0.0.1:11434/api/generate"

if (-not (Test-Path -LiteralPath $inputPath)) {
  throw "Missing prompt input file: $inputPath"
}

$records = Get-Content -LiteralPath $inputPath | ForEach-Object {
  if ($_ -and $_.Trim()) { $_ | ConvertFrom-Json }
}

$writer = [System.IO.StreamWriter]::new($outputPath, $false, [System.Text.Encoding]::UTF8)
$failureWriter = [System.IO.StreamWriter]::new($failurePath, $false, [System.Text.Encoding]::UTF8)
try {
  foreach ($record in $records) {
    try {
      $safePrompt = [regex]::Replace([string]$record.prompt, "[\x00-\x08\x0B\x0C\x0E-\x1F]", " ")
      $body = @{
        model = $record.generator_model
        prompt = $safePrompt
        stream = $false
        format = "json"
        options = @{ temperature = 0.2 }
      } | ConvertTo-Json -Depth 8

      $response = Invoke-RestMethod -Method Post -Uri $ollamaUrl -ContentType "application/json" -Body $body
      $generated = $response.response | ConvertFrom-Json

      $out = [ordered]@{
        id = $record.id
        domain = $record.domain
        messages = @(
          @{ role = "system"; content = "You are a fitness and nutrition assistant grounded in evidence-based exercise physiology and sports nutrition." }
          @{ role = "user"; content = $record.seed.user_query }
          @{ role = "assistant"; content = $generated.assistant }
        )
        screening_points = @($generated.screening_points)
        evidence_used = @($generated.evidence_used)
        retrieved_evidence = @($record.retrieved_evidence)
        generator_model = $record.generator_model
        embedding_model = $record.embedding_model
      }

      $writer.WriteLine(($out | ConvertTo-Json -Depth 10 -Compress))
      $writer.Flush()
      Write-Host ("generated " + $record.id)
    }
    catch {
      $failure = [ordered]@{
        id = $record.id
        domain = $record.domain
        error = $_.Exception.Message
      }
      $failureWriter.WriteLine(($failure | ConvertTo-Json -Compress))
      $failureWriter.Flush()
      Write-Warning ("failed " + $record.id + ": " + $_.Exception.Message)
    }
  }
}
finally {
  $writer.Dispose()
  $failureWriter.Dispose()
}

Write-Host ("wrote " + $outputPath)
Write-Host ("wrote " + $failurePath)
