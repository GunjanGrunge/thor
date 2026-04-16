param(
  [string]$InputPath = "",
  [string]$OutputPath = "",
  [string]$FailurePath = "",
  [string]$ModelId = "google.gemma-3-4b-it",
  [string]$Region = "us-east-1",
  [string]$EnvPath = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$inputPath = if ($InputPath) { $InputPath } else { Join-Path $root "data\sft\grounded_generation_inputs.jsonl" }
$outputPath = if ($OutputPath) { $OutputPath } else { Join-Path $root "data\sft\grounded_examples_bedrock.jsonl" }
$failurePath = if ($FailurePath) { $FailurePath } else { Join-Path $root "data\sft\grounded_generation_failures_bedrock.jsonl" }
$envPath = if ($EnvPath) { $EnvPath } else { Join-Path $root ".env" }

function Set-EnvFromDotenv {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    return
  }

  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
      return
    }
    $parts = $line.Split("=", 2)
    if ($parts.Count -ne 2) {
      return
    }
    $name = $parts[0].Trim()
    $value = $parts[1].Trim()
    if ($name) {
      [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
  }
}

function Extract-AssistantJson {
  param([string]$Text)

  if (-not $Text) {
    return $null
  }

  $trimmed = $Text.Trim()
  if ($trimmed.StartsWith('```')) {
    $trimmed = [regex]::Replace($trimmed, '^```(?:json)?\s*', '')
    $trimmed = [regex]::Replace($trimmed, '\s*```$', '')
  }

  try {
    return $trimmed | ConvertFrom-Json
  }
  catch {
    return $null
  }
}

function Get-BedrockAssistantText {
  param($Response)

  if ($null -eq $Response -or $null -eq $Response.output -or $null -eq $Response.output.message) {
    return ""
  }

  $parts = @()
  foreach ($item in @($Response.output.message.content)) {
    if ($null -eq $item) {
      continue
    }
    if ($item.PSObject.Properties.Name -contains "text" -and $item.text) {
      $parts += [string]$item.text
      continue
    }
    if ($item.PSObject.Properties.Name -contains "reasoningContent") {
      continue
    }
  }

  return ($parts -join "`n").Trim()
}

function Sanitize-BedrockPrompt {
  param([string]$Text)

  if (-not $Text) {
    return ""
  }

  $clean = [regex]::Replace($Text, "[^\u0009\u000A\u000D\u0020-\u007E]", " ")
  return [regex]::Replace($clean, "\s+", " ").Trim()
}

if (-not (Test-Path -LiteralPath $inputPath)) {
  throw "Missing prompt input file: $inputPath"
}

Set-EnvFromDotenv -Path $envPath

$records = Get-Content -LiteralPath $inputPath | ForEach-Object {
  if ($_ -and $_.Trim()) { $_ | ConvertFrom-Json }
}

$writer = [System.IO.StreamWriter]::new($outputPath, $false, [System.Text.Encoding]::UTF8)
$failureWriter = [System.IO.StreamWriter]::new($failurePath, $false, [System.Text.Encoding]::UTF8)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

try {
  foreach ($record in $records) {
    $requestPath = Join-Path $root "bedrock_request_tmp.json"
    try {
      $request = [ordered]@{
        modelId = $ModelId
        messages = @(
          @{
            role = "user"
            content = @(
              @{ text = (Sanitize-BedrockPrompt -Text ([string]$record.prompt)) }
            )
          }
        )
        inferenceConfig = @{
          temperature = 0.1
          maxTokens = 900
        }
      } | ConvertTo-Json -Depth 10

      [System.IO.File]::WriteAllText($requestPath, $request, $utf8NoBom)
      $response = aws bedrock-runtime converse --region $Region --cli-input-json ("file://" + $requestPath) --output json | ConvertFrom-Json

      $assistantText = Get-BedrockAssistantText -Response $response
      if (-not $assistantText) {
        throw "model response did not contain assistant text content"
      }
      $generated = Extract-AssistantJson -Text $assistantText
      if ($null -eq $generated) {
        throw "model response was not valid JSON"
      }

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
        generator_model = $ModelId
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
        model = $ModelId
      }
      $failureWriter.WriteLine(($failure | ConvertTo-Json -Compress))
      $failureWriter.Flush()
      Write-Warning ("failed " + $record.id + ": " + $_.Exception.Message)
    }
    finally {
      if (Test-Path -LiteralPath $requestPath) {
        Remove-Item -LiteralPath $requestPath -Force
      }
    }
  }
}
finally {
  $writer.Dispose()
  $failureWriter.Dispose()
}

Write-Host ("wrote " + $outputPath)
Write-Host ("wrote " + $failurePath)
