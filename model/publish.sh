#!/usr/bin/env bash
set -euo pipefail

##
## Publish the fine-tuned compliance model to ollama.com.
##
## `air-blackbox setup` and the CLI's deep scan pull airblackbox/air-compliance,
## so publishing here updates every install that runs setup again.
##
## Needs, on the machine you run this from:
##   - Ollama installed and running
##   - that machine's Ollama key (~/.ollama/id_ed25519.pub) added to the
##     ollama.com account that owns the "airblackbox" namespace
##     (ollama.com → Settings → Ollama keys)
##   - the GGUF at model/air-compliance-v3.gguf
##
## Usage:
##   bash model/publish.sh v3
##
## Pushes airblackbox/air-compliance:<version> and :latest, and prints the
## GGUF's SHA-256 for AIR_GGUF_SHA256 in deploy-enterprise.sh.
##

VERSION="${1:?usage: bash model/publish.sh <version, e.g. v3>}"
NAME="${AIR_COMPLIANCE_MODEL_NAME:-airblackbox/air-compliance}"
GGUF="air-compliance-v3.gguf"

cd "$(dirname "$0")"
[ -f "$GGUF" ] || { echo "✗ model/$GGUF not found" >&2; exit 1; }
command -v ollama > /dev/null || { echo "✗ Ollama is not installed" >&2; exit 1; }

if command -v sha256sum > /dev/null; then
    SHA="$(sha256sum "$GGUF" | cut -d' ' -f1)"
else
    SHA="$(shasum -a 256 "$GGUF" | cut -d' ' -f1)"   # macOS
fi

echo "→ Creating $NAME:$VERSION from model/Modelfile..."
ollama create "$NAME:$VERSION" -f Modelfile

echo "→ Pushing $NAME:$VERSION..."
ollama push "$NAME:$VERSION"

echo "→ Pointing $NAME:latest at $VERSION..."
ollama cp "$NAME:$VERSION" "$NAME:latest"
ollama push "$NAME:latest"

echo ""
echo "Published $NAME:$VERSION (also :latest)."
echo "  GGUF SHA-256 (AIR_GGUF_SHA256): $SHA"
echo "  Check from another machine: ollama pull $NAME:$VERSION"
echo "  Existing installs update with: air-blackbox setup"
