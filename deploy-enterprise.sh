#!/usr/bin/env bash
set -euo pipefail

##
## AIR Blackbox Enterprise — One-Command VPS Deployment
##
## Prerequisites: Ubuntu 22.04+ with SSH access and sudo; 8 GB RAM recommended.
## This script installs Docker, fetches the repo, and starts all services.
## Run it again to update: it pulls the repo and rebuilds, keeping .env.
##
## Usage:
##   ssh root@your-vps "bash <(curl -sL https://raw.githubusercontent.com/airblackbox/airblackbox/main/deploy-enterprise.sh)"
##
## Or clone and run locally:
##   git clone https://github.com/airblackbox/airblackbox.git
##   cd airblackbox
##   bash deploy-enterprise.sh
##
## The fine-tuned model is not in the repository. Either copy it to
## model/air-compliance-v3.gguf first, or let the script download it:
##   AIR_GGUF_URL       where to download the GGUF from
##   AIR_GGUF_SHA256    its SHA-256 (required with AIR_GGUF_URL)
##   AIR_GGUF_TOKEN     optional bearer token for a private URL
##
## Remote access for your team (HTTPS with a Let's Encrypt certificate):
##   AIR_DOMAIN         DNS name pointing at this server, e.g. air.acme.com
## Ports 80 and 443 must be open. Without AIR_DOMAIN everything stays bound
## to 127.0.0.1.
##
## Secrets are generated once and kept in .env (mode 600). Running the
## script again never replaces them: a new TRUST_SIGNING_KEY would leave
## the existing audit chain unverifiable.
##

REPO_URL="https://github.com/airblackbox/airblackbox.git"
INSTALL_DIR="/opt/air-blackbox"
MODEL_FILE="model/air-compliance-v3.gguf"
COMPOSE=(docker compose -f docker-compose.enterprise.yaml)

die() { echo "✗ $*" >&2; exit 1; }

# Value of NAME in .env, or empty.
env_get() {
    [ -f .env ] || return 0
    grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true
}

# Write NAME=VALUE to .env unless NAME already has a value there.
env_keep() {
    if [ -z "$(env_get "$1")" ]; then
        printf '%s=%s\n' "$1" "$2" >> .env
        return 0
    fi
    return 1
}

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

# ── 2. Fetch or update the repository ────────────────────────
if [ -f "docker-compose.enterprise.yaml" ]; then
    echo "→ Using the repository in $(pwd)."
elif [ -d "$INSTALL_DIR/.git" ]; then
    echo "→ Updating $INSTALL_DIR..."
    cd "$INSTALL_DIR"
    git pull --ff-only
else
    echo "→ Cloning AIR Blackbox into $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

touch .env
chmod 600 .env

# ── 3. Secrets (generated once, kept in .env) ────────────────
env_keep TRUST_SIGNING_KEY "$(openssl rand -hex 32)" && echo "→ Generated TRUST_SIGNING_KEY (saved to .env)"
env_keep MINIO_USER "airblackbox" || true
env_keep MINIO_PASS "$(openssl rand -hex 16)" && echo "→ Generated vault credentials (saved to .env)"
env_keep GATEWAY_KEY "$(openssl rand -hex 24)" && echo "→ Generated GATEWAY_KEY (saved to .env)"

# ── 4. Remote access ─────────────────────────────────────────
if [ -n "${AIR_DOMAIN:-}" ]; then
    env_keep AIR_DOMAIN "$AIR_DOMAIN" || true
fi
AIR_DOMAIN="$(env_get AIR_DOMAIN)"
if [ -n "$AIR_DOMAIN" ]; then
    echo "→ Remote access on https://${AIR_DOMAIN}"
    getent hosts "$AIR_DOMAIN" > /dev/null \
        || echo "  ⚠  ${AIR_DOMAIN} does not resolve yet. The certificate is issued once it points here."
    env_keep COMPOSE_PROFILES "remote" || true
    env_keep JAEGER_USER "air" || true
    if [ -z "$(env_get JAEGER_PASSWORD_HASH)" ]; then
        JAEGER_PASSWORD="$(openssl rand -hex 12)"
        HASH="$(docker run --rm caddy:2.11-alpine caddy hash-password --plaintext "$JAEGER_PASSWORD")"
        # Single quotes: the bcrypt hash contains $, which Compose would
        # otherwise read as a variable.
        printf "JAEGER_PASSWORD=%s\nJAEGER_PASSWORD_HASH='%s'\n" "$JAEGER_PASSWORD" "$HASH" >> .env
        echo "→ Generated the Jaeger password (saved to .env)"
    fi
fi

# ── 5. Create runs directory ──────────────────────────────────
mkdir -p runs
echo "→ Runs directory ready."

# ── 6. The fine-tuned model ───────────────────────────────────
if [ ! -f "$MODEL_FILE" ] && [ -n "${AIR_GGUF_URL:-}" ]; then
    [ -n "${AIR_GGUF_SHA256:-}" ] || die "Set AIR_GGUF_SHA256 with AIR_GGUF_URL, so the download can be checked."
    echo "→ Downloading the compliance model..."
    AUTH=()
    [ -n "${AIR_GGUF_TOKEN:-}" ] && AUTH=(-H "Authorization: Bearer ${AIR_GGUF_TOKEN}")
    curl -fL --retry 3 "${AUTH[@]}" -o "${MODEL_FILE}.part" "$AIR_GGUF_URL"
    echo "${AIR_GGUF_SHA256}  ${MODEL_FILE}.part" | sha256sum -c --quiet - \
        || { rm -f "${MODEL_FILE}.part"; die "The downloaded model does not match AIR_GGUF_SHA256."; }
    mv "${MODEL_FILE}.part" "$MODEL_FILE"
fi
if [ ! -f "$MODEL_FILE" ]; then
    echo ""
    echo "⚠  $MODEL_FILE not found."
    echo "   Copy the fine-tuned model there, or set AIR_GGUF_URL and AIR_GGUF_SHA256."
    echo ""
    exit 1
fi
if [ -n "${AIR_GGUF_SHA256:-}" ]; then
    echo "${AIR_GGUF_SHA256}  ${MODEL_FILE}" | sha256sum -c --quiet - \
        || die "$MODEL_FILE does not match AIR_GGUF_SHA256."
fi

# ── 7. Build and start the stack ─────────────────────────────
echo ""
echo "→ Building and starting the stack..."
echo "  (The first build bakes the 1.3 GB model into an image.)"
"${COMPOSE[@]}" up -d --build --wait --wait-timeout 600

GATEWAY_KEY="$(env_get GATEWAY_KEY)"
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║           Deployment Complete!               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  On this server:"
echo "    Gateway API:   http://localhost:8080"
echo "    Jaeger UI:     http://localhost:16686/jaeger"
echo "    Vault console: http://localhost:9001"
echo "    Health check:  curl http://localhost:8080/health"
echo ""
if [ -n "$AIR_DOMAIN" ]; then
    echo "  For your team (each person, once):"
    echo "    pip install air-blackbox"
    echo "    export AIR_GATEWAY_URL=https://${AIR_DOMAIN}"
    echo "    export AIR_MODEL_SERVER=https://${AIR_DOMAIN}"
    echo "    export AIR_GATEWAY_KEY=${GATEWAY_KEY}"
    echo "    air-blackbox comply --scan ."
    echo ""
    echo "    Jaeger:   https://${AIR_DOMAIN}/jaeger"
    echo "              user $(env_get JAEGER_USER), password in .env (JAEGER_PASSWORD)"
else
    echo "  Ports are bound to 127.0.0.1. For your team, run again with"
    echo "  AIR_DOMAIN=<a DNS name pointing here>, or use an SSH tunnel."
    echo ""
    echo "  Run a compliance scan here:"
    echo "    pip install air-blackbox"
    echo "    export AIR_GATEWAY_KEY=${GATEWAY_KEY}"
    echo "    air-blackbox comply --scan /path/to/project --model-server http://localhost:8080"
fi
echo ""
echo "  ⚠  Traces, records and the model stay on this server."
