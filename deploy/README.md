# AIR Blackbox - Deployment

## Quick Start (Core Stack)

From the repo root:

```bash
cp .env.example .env   # add your OPENAI_API_KEY
docker compose up
```

This starts: Gateway (`:8080`), MinIO (`:9000`), OTel Collector, Jaeger (`:16686`).

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
| MinIO Console | 9001 | http://localhost:9001 |
| Prometheus | 9091 | http://localhost:9091 |
| OTel gRPC | 4317 | - |
| OTel HTTP | 4318 | - |

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
