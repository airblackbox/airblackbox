# The compliance model

The deep scan in `air-blackbox comply` runs a fine-tuned model through
Ollama. It is published on ollama.com as `airblackbox/air-compliance`.

## Install or update it

```bash
air-blackbox setup
```

This pulls `airblackbox/air-compliance` and points the local
`air-compliance` name, which the scanner uses, at it. Run it again after a new
version is published to update. To pin a version, or to pull from a mirror:

```bash
export AIR_COMPLIANCE_MODEL=airblackbox/air-compliance:v3
air-blackbox setup
```

On a dedicated AIR server the model is baked into a local Docker image
instead (`docker-compose.enterprise.yaml`, `deploy-enterprise.sh`), and
teammates run the deep scan on it with `AIR_MODEL_SERVER`.

## Publish a new version

With the GGUF at `model/air-compliance-v3.gguf`, Ollama installed, and this
machine's Ollama key (`~/.ollama/id_ed25519.pub`) added to the ollama.com
account that owns the `airblackbox` namespace:

```bash
bash model/publish.sh v3
```

It pushes `airblackbox/air-compliance:v3` and `:latest` from `Modelfile`,
and prints the GGUF's SHA-256 for `AIR_GGUF_SHA256` in
`deploy-enterprise.sh`. `Modelfile` names the GGUF by a relative path, so the
same file builds the server image and the published model.

## What the scanner expects back

The scanner's prompt asks for a status per article (Articles 9, 10, 11, 12,
14, 15). It reads JSON, `Article N - Name: PASS|WARN|FAIL` markdown, and the
`FINDING / ARTICLE / SEVERITY / EVIDENCE / RECOMMENDATION` blocks the system
prompt in `Modelfile` asks for. A model whose answers match none of these adds
no findings to the scan.
