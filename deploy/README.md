# AIR Blackbox — Deployment

## Quick Start (Core Stack)

From the repo root:

```bash
cp .env.example .env   # add your OPENAI_API_KEY
docker compose up
```

This starts: Gateway (`:8080`), the vault (`:9000`), OTel Collector, Jaeger (`:16686`).

The vault is [Silo](https://silo.pgsty.com), a maintained MinIO fork with the
same commands, variables and S3 API: MinIO deleted `minio/minio` from Docker
Hub. Set `VAULT_IMAGE` to run another S3-compatible image instead.

## Full Stack (with Prometheus)

```bash
cd deploy/
make up
```

Adds Prometheus (`:9091`) for metrics collection.

## Services

| Service | Port | URL |
|---------|------|-----|
| Gateway | 8080 | http://localhost:8080 |
| Jaeger UI | 16686 | http://localhost:16686 |
| Vault console | 9001 | http://localhost:9001 |
| Prometheus | 9091 | http://localhost:9091 |
| OTel gRPC | 4317 | — |
| OTel HTTP | 4318 | — |

## Dedicated Server (fine-tuned model, nothing leaves the machine)

`deploy-enterprise.sh` sets up `docker-compose.enterprise.yaml` on a VPS: the
gateway in front of Ollama with the fine-tuned compliance model baked into a
local image, the collector with a local-only pipeline, Jaeger and the vault.

```bash
# the model is not in the repository: copy it in, or let the script fetch it
export AIR_GGUF_URL=https://...  AIR_GGUF_SHA256=<sha256 of the file>
# optional: HTTPS for your team (DNS must point here, ports 80 and 443 open)
export AIR_DOMAIN=air.example.com
bash deploy-enterprise.sh
```

It generates the signing key, vault credentials, `GATEWAY_KEY` and, with
`AIR_DOMAIN`, a Jaeger password, all once, into `.env`. Running it again
updates the repository and rebuilds without touching them.

With `AIR_DOMAIN`, Caddy serves `https://AIR_DOMAIN/v1/...` (the gateway,
which requires the `X-Gateway-Key` header) and `https://AIR_DOMAIN/jaeger`
(behind the Jaeger password). Ollama, the collector and the vault are not
exposed. Each teammate then sets, once:

```bash
export AIR_GATEWAY_URL=https://air.example.com   # runtime checks read the server's records
export AIR_MODEL_SERVER=https://air.example.com  # deep scan runs on the server's model
export AIR_GATEWAY_KEY=<GATEWAY_KEY from the server's .env>
air-blackbox comply --scan .
```

## After Starting

```bash
# Check compliance status
air-blackbox comply -v

# See what models are in use
air-blackbox discover

# View audit trail
air-blackbox replay
```

## Make Commands

```bash
make up        # Start full stack
make down      # Stop everything
make status    # Check service health
make logs      # Tail gateway logs
make comply    # Run compliance check
make demo      # Generate demo data + check
make clean     # Remove all data volumes
```
