#!/usr/bin/env bash
set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  git \
  gnupg \
  lsb-release

mkdir -p /etc/apt/keyrings
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  gpg --dearmor -o /etc/apt/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/etc/apt/keyrings/nvidia-container-toolkit-keyring.gpg] https://#' | \
  tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

apt-get update
apt-get install -y nvidia-container-toolkit

if ! command -v docker >/dev/null 2>&1; then
  apt-get install -y --no-install-recommends \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin
fi

nvidia-ctk runtime configure --runtime=docker
systemctl enable --now docker
systemctl restart docker

for user in ubuntu ec2-user admin; do
  if id "$user" >/dev/null 2>&1; then
    usermod -aG docker "$user"
  fi
done

mkdir -p /var/log/thor
docker --version >/var/log/thor/docker-version.txt 2>&1 || true
docker compose version >/var/log/thor/docker-compose-version.txt 2>&1 || true
