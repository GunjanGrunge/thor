param(
    [string]$EnvFile = ".env",
    [string]$Region = "us-east-1",
    [string]$ImageId = "ami-06abbbf2049359343",
    [string]$InstanceType = "g6.xlarge",
    [string]$KeyName = "thor-training-20260416-184056",
    [string]$SecurityGroupId = "sg-08cd5cc3e66e65c46",
    [string]$SubnetId = "subnet-0bf7acf3a06b15472",
    [string]$InstanceName = "Thor-Docker-Training",
    [int]$RootVolumeSize = 150,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
    throw "Missing env file: $EnvFile"
}

$envLines = Get-Content $EnvFile | Where-Object { $_ -match '^[A-Z0-9_]+=' }
foreach ($line in $envLines) {
    $k, $v = $line -split '=', 2
    if ($k -in @('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION')) {
        [Environment]::SetEnvironmentVariable($k, $v, 'Process')
    }
}

if (-not $env:AWS_REGION) {
    $env:AWS_REGION = $Region
}

$tmpDir = Join-Path $PWD "outputs\\tmp"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
$blockFile = Join-Path $tmpDir "thor_block_device_mappings.json"
$blockDeviceMappingsJson = @"
[
  {
    "DeviceName": "/dev/sda1",
    "Ebs": {
      "VolumeSize": $RootVolumeSize,
      "VolumeType": "gp3",
      "DeleteOnTermination": true
    }
  }
]
"@
$blockDeviceMappingsJson | Set-Content -Path $blockFile -Encoding ascii
$blockDeviceMappingsShorthand = "DeviceName=/dev/sda1,Ebs={VolumeSize=$RootVolumeSize,VolumeType=gp3,DeleteOnTermination=true}"

$keyCheck = python -m awscli ec2 describe-key-pairs `
    --region $env:AWS_REGION `
    --key-names $KeyName `
    --query "KeyPairs[0].KeyName" `
    --output text

if ($LASTEXITCODE -ne 0 -or $keyCheck -ne $KeyName) {
    throw "Missing or inaccessible EC2 key pair: $KeyName"
}

$sgCheck = python -m awscli ec2 describe-security-groups `
    --region $env:AWS_REGION `
    --group-ids $SecurityGroupId `
    --query "SecurityGroups[0].GroupId" `
    --output text

if ($LASTEXITCODE -ne 0 -or $sgCheck -ne $SecurityGroupId) {
    throw "Missing or inaccessible security group: $SecurityGroupId"
}

$awsArgs = @(
    "-m", "awscli", "ec2", "run-instances",
    "--region", $env:AWS_REGION,
    "--image-id", $ImageId,
    "--instance-type", $InstanceType,
    "--key-name", $KeyName,
    "--security-group-ids", $SecurityGroupId,
    "--subnet-id", $SubnetId,
    "--block-device-mappings", $blockDeviceMappingsShorthand,
    "--tag-specifications", "ResourceType=instance,Tags=[{Key=Name,Value=$InstanceName}]",
    "--output", "json"
)

if ($DryRun) {
    $awsArgs += "--dry-run"
}

python @awsArgs
