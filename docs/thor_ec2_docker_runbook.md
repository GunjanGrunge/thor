# Thor EC2 Docker Runbook

This is the only AWS flow that should be used for Thor Docker training.
Do not start a smoke run or full training run until the image rebuild and
header validation step has passed.

## Purpose

This runbook avoids the loop we hit previously:

- new instance
- partial bootstrap
- unclear image state
- smoke run against stale image
- expensive failure

The guarded sequence is now:

1. bootstrap instance once
2. upload clean Thor bundle
3. rebuild Docker image with `--no-cache`
4. validate `Python.h` exists inside the built image
5. start 1-step smoke run
6. only then start real training

## Required Inputs

- `HOST`
- Thor SSH key file already available through:
  - `scripts/thor_ec2_ssh_wsl.sh`
- repo present locally at:
  - `/mnt/c/Users/Bot/Desktop/Thor`

## One-Command Smoke Preflight

From local WSL:

```bash
cd /mnt/c/Users/Bot/Desktop/Thor
HOST=<ec2-public-dns> bash scripts/run_remote_thor_smoke_preflight_wsl.sh
```

What this does:

1. uploads the Thor Docker bundle to `/home/ubuntu`
2. runs a remote no-cache rebuild of `thor-unsloth:latest`
3. validates `/usr/include/python3.10/Python.h` inside the built image
4. uploads the smoke launcher
5. starts the 1-step smoke run

If step 2 or 3 fails, the smoke run is not started.

## Runtime Verification

Before the guarded smoke path, verify that both the host and Docker can see the
GPU using the dedicated remote script:

```bash
cd /mnt/c/Users/Bot/Desktop/Thor
HOST=<ec2-public-dns> bash scripts/run_remote_thor_verify_runtime_wsl.sh
```

This avoids the nested local/remote shell quoting issues that previously caused
checks to execute partly on the local WSL machine instead of the EC2 host.

## Safe Instance Launch

Do not handcraft the EC2 launch JSON in an ad hoc PowerShell command.
Use the dedicated launcher from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_thor_ec2.ps1
```

This launcher:

- reads AWS credentials from `.env`
- writes block-device mappings to a temporary JSON file
- calls `python -m awscli ec2 run-instances`
- avoids the inline JSON quoting failure that previously blocked launch

## Monitoring

Smoke log:

```bash
HOST=<ec2-public-dns> bash scripts/thor_ec2_ssh_wsl.sh tail -f /home/ubuntu/outputs/qwenf1/train_logs/aws_phase12_docker_smoke.log
```

Quick process + GPU snapshot:

```bash
HOST=<ec2-public-dns> bash scripts/thor_ec2_ssh_wsl.sh bash -lc 'ps -ef | grep -E "docker-buildx|docker-compose|train_qwenf1|python" | grep -v grep || true; echo ---; nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits'
```

## Success Criteria For Smoke

Smoke is considered healthy only if the log shows:

- container starts cleanly
- no stale `outputs/training.lock` failure
- no `Python.h` / Triton compile error
- torch sees CUDA
- Unsloth/model startup begins

The smoke run does not need to finish a meaningful train. It only needs to
prove the Docker runtime path is valid.

## After Smoke Passes

Only after the smoke run passes should you start a real training run on the
same instance. Reusing the same instance avoids paying the first-build cost
again.

## Same-Instance Repo Refresh

If you are reusing the same EC2 instance and only want to push repo changes
without rebuilding the Docker image, sync the repo in place:

```bash
cd /mnt/c/Users/Bot/Desktop/Thor
HOST=<ec2-public-dns> bash scripts/sync_thor_repo_to_ec2_wsl.sh
```

Then start the strict phased run on that same instance:

```bash
HOST=<ec2-public-dns> bash scripts/thor_ec2_ssh_wsl.sh bash /workspace/Thor/scripts/remote_phase12_start.sh
```

## Known Rules

- Do not use `.env` with docker compose directly. Use `--env-file .env.example`.
- Do not start full training from a fresh instance until the guarded smoke path
  has passed.
- Do not keep launching new instances to debug image state. Fix repo-side
  scripts first, then do one clean launch.
