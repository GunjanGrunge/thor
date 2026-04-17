import os
from pathlib import Path
import subprocess

env_path = Path("C:/Users/Bot/Desktop/Thor/.env")
creds = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"):
        creds[key] = value
os.environ.update(creds)

cmd = [
    "python",
    "-m",
    "awscli",
    "ec2",
    "describe-instances",
    "--instance-ids",
    "i-0c83276e74c92c261",
    "--region",
    os.environ["AWS_REGION"],
    "--query",
    "Reservations[0].Instances[0].{State:State.Name,PublicDnsName:PublicDnsName,PublicIpAddress:PublicIpAddress,PrivateIpAddress:PrivateIpAddress,SubnetId:SubnetId}",
    "--output",
    "json",
]
proc = subprocess.run(cmd, capture_output=True, text=True)
print(proc.stdout)
print(proc.stderr, end="")
exit(proc.returncode)
