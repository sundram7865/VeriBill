#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 EC2 instance: Docker Engine + Compose plugin, swap,
# and the app directory. Run as the default "ubuntu" user: bash bootstrap.sh
set -euo pipefail

APP_DIR=/opt/veribill
SWAP_SIZE=${SWAP_SIZE:-2G}

echo "==> Installing Docker Engine and the Compose plugin (official apt repository)"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"

# Free-tier instances have 1-2 GB of RAM; swap keeps OCR spikes from triggering the OOM killer.
if ! swapon --show | grep -q /swapfile; then
  echo "==> Creating ${SWAP_SIZE} swap file"
  sudo fallocate -l "$SWAP_SIZE" /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo "==> Preparing ${APP_DIR}"
sudo mkdir -p "$APP_DIR/backups"
sudo chown -R "$USER":"$USER" "$APP_DIR"

echo "Done. Log out and back in (docker group), then copy compose.prod.yml, scripts/ and .env"
echo "into ${APP_DIR} and run scripts/deploy.sh. See docs/DEPLOY.md."
