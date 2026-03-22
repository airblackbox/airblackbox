#!/usr/bin/env bash
set -euo pipefail

##
## AIR Blackbox Enterprise — One-Command VPS Deployment
##
## Prerequisites: Ubuntu 22.04+ with SSH access and sudo.
## This script installs Docker, pulls the repo, and starts all services.
##
## Usage:
##   ssh root@your-vps "bash <(curl -sL https://raw.githubusercontent.com/airblackbox/gateway/main/deploy-enterprise.sh)"
##
## Or clone and run locally:
##   git clone https://github.com/airblackbox/gateway.git
##   cd gateway
##   bash deploy-enterprise.sh
##

echo "╔══════════════════════════════════════════════╗"
echo "║  AIR Blackbox Enterprise — Air-Gapped Setup  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. Install Docker if not present ─────────────────────────
if ! command -v docker &> /dev/null; then
    echo "→ Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "  Docker installed."
else
    echo "→ Docker already installed."
fi

# Ensure docker compose plugin is available
if ! docker compose version &> /dev/null; then
    echo "→ Installing Docker Compose plugin..."
    apt-get update -qq && apt-get install -y -qq docker-compose-plugin
fi

# ── 2. Clone repo if not in gateway directory ─────────────────
if [ ! -f "docker-compose.enterprise.yaml" ]; then
    echo "→ Cloning AIR Blackbox gateway..."
    git clone https://github.com/airblackbox/gateway.git /opt/air-blackbox
    cd /opt/air-blackbox
else
    echo "→ Already in gateway directory."
fi

# ── 3. Generate signing key if not set ────────────────────────
if [ -z "${TRUST_SIGNING_KEY:-}" ]; then
    TRUST_SIGNING_KEY=$(openssl rand -hex 32)
    echo "TRUST_SIGNING_KEY=${TRUST_SIGNING_KEY}" >> .env
    echo "→ Generated TRUST_SIGNING_KEY (saved to .env)"
fi

# ── 4. Generate MinIO credentials if not set ──────────────────
if [ -z "${MINIO_USER:-}" ]; then
    MINIO_USER="airblackbox"
    MINIO_PASS=$(openssl rand -hex 16)
    echo "MINIO_USER=${MINIO_USER}" >> .env
    echo "MINIO_PASS=${MINIO_PASS}" >> .env
    echo "→ Generated MinIO credentials (saved to .env)"
fi

# ── 5. Create runs directory ──────────────────────────────────
mkdir -p runs
echo "→ Runs directory ready."

# ── 6. Build the custom Ollama image with fine-tuned model ────
if [ ! -f "model/air-compliance-v3.gguf" ]; then
    echo ""
    echo "⚠  model/air-compliance-v3.gguf not found."
    echo "   Copy the fine-tuned model before deploying:"
    echo "   cp /path/to/air-compliance-v3.gguf model/air-compliance-v3.gguf"
    echo ""
    exit 1
fi

echo ""
echo "→ Building Ollama image with fine-tuned compliance model..."
echo "  (This bakes the 1.3GB model into the Docker image — one-time build)"
docker build -f model/Dockerfile.ollama -t airblackbox/ollama-compliance:v3 .

# ── 7. Start the stack ────────────────────────────────────────
echo ""
echo "→ Starting AIR Blackbox Enterprise stack..."
docker compose -f docker-compose.enterprise.yaml up -d --build

echo ""
echo "→ Waiting for Ollama to be healthy..."
docker compose -f docker-compose.enterprise.yaml logs -f ollama 2>&1 | grep -m1 "Listening" || sleep 15

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║           Deployment Complete!               ║"
echo "╠══════════════════════════════════════════════╣"
echo "║                                              ║"
echo "║  Gateway API:    http://localhost:8080        ║"
echo "║  Jaeger UI:      http://localhost:16686       ║"
echo "║  MinIO Console:  http://localhost:9001        ║"
echo "║                                              ║"
echo "║  All ports bound to 127.0.0.1 (localhost).   ║"
echo "║  Use SSH tunnel or reverse proxy for         ║"
echo "║  remote access.                              ║"
echo "║                                              ║"
echo "║  Test it:                                    ║"
echo "║  curl http://localhost:8080/healthz           ║"
echo "║                                              ║"
echo "║  Run a compliance scan:                      ║"
echo "║  pip install air-blackbox                    ║"
echo "║  air-blackbox comply --scan                  ║"
echo "║                                              ║"
echo "║  ⚠  AIR-GAPPED: No data leaves this server. ║"
echo "╚══════════════════════════════════════════════╝"
