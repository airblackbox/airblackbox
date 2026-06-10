# High Availability Deployment

How to run AIR Blackbox Gateway with multiple replicas, what scales cleanly,
and what you need to know about per-replica state. This document is honest
about the current architecture. No hand-waving.

## Quick start

```bash
helm install air ./deploy/helm/air-gateway \
  --set providerURL=https://api.openai.com \
  --set vault.endpoint=your-s3-endpoint:9000 \
  --set vault.existingSecret=air-vault-creds
```

This deploys 2 stateless gateway replicas behind a Service, with pod
anti-affinity so they land on different nodes, readiness and liveness probes
on `/health`, and optional HPA.

## What scales cleanly

**Proxying.** The gateway is stateless on the request path. Any replica can
serve any request. Add replicas, the Service load-balances, done.

**The content vault.** All replicas point at the same S3-compatible bucket.
Vaulted prompts and completions are shared, durable state. This is where your
sensitive content lives, and it scales with your object store.

**OTel export.** All replicas export to the same collector endpoint. Traces
from every replica land in one backend.

**The witness contract.** Each replica independently guarantees non-blocking
behavior. A replica with an unreachable vault still proxies. Kubernetes
restarting an unhealthy replica never drops in-flight requests on the others.

## What is per-replica (read this part)

**The HMAC audit chain is in-memory, per replica.** Each gateway instance
maintains its own chain. With 3 replicas you have 3 chains, and each chain is
individually complete and verifiable: every entry links to the previous
entry's hash within that replica, and `verify.py` validates each one
independently. What you do NOT get today is a single global ordering across
replicas.

**AIR record files (`RUNS_DIR`) are local, per replica.** The Helm chart
mounts an emptyDir by default. Records are best-effort local artifacts; the
durable content reference is the vault.

**Practical consequence for evidence export:** collect evidence from each
replica, not just the Service (which would hit one random pod):

```bash
for pod in $(kubectl get pods -l app.kubernetes.io/name=air-gateway -o name); do
  kubectl port-forward "$pod" 8080:8080 &
  sleep 2
  curl -s http://localhost:8080/v1/audit/export > "evidence-$(basename $pod).json"
  kill %1
done
```

Each bundle is independently signed and verifiable. For an auditor, N valid
chains from N replicas is acceptable evidence. It is more chains, not weaker
chains.

**Chain lifetime equals pod lifetime.** A restarted pod starts a fresh chain.
If your compliance posture requires unbroken chains across restarts, export
evidence on a schedule (a CronJob hitting `/v1/audit/export` per pod) so every
chain segment is captured before its pod recycles.

## Storage roadmap: pluggable chain and episode backends

The current design is correct for single-node and acceptable for small HA
deployments. The next step, planned, is a pluggable storage interface:

```
ChainStore interface
  Append(entry) error
  Entries(since) ([]Entry, error)
  Head() (Entry, error)
```

- **Default: in-memory** (today's behavior, zero infrastructure)
- **Postgres backend**: single global chain across replicas, survives
  restarts, serializable append ordering
- **ClickHouse backend**: trace-volume episode storage at scale

Until then, the per-replica model above is the supported HA configuration,
and it is sufficient for evidence purposes because chain validity is
per-chain, not per-fleet.

## Sizing guidance

Start with the chart defaults (2 replicas, 250m CPU / 256Mi requests). The
gateway's hot path is HTTP proxying plus hashing, which is cheap. Run
`bench/run-bench.sh` on hardware comparable to your nodes and divide your
expected peak RPS by the single-node ceiling to pick a replica count, then
add one for failure headroom.

## Failure behavior in Kubernetes

| Failure | Behavior |
|---------|----------|
| One replica crashes | Service routes around it; liveness probe restarts it; its chain restarts fresh |
| Vault unreachable | All replicas keep proxying; vault writes fail gracefully (witness contract) |
| Collector unreachable | All replicas keep proxying; spans drop silently |
| Node loss | Anti-affinity means the other replica is on a different node |
| Provider down | Gateway returns the provider's errors; the gateway adds no failure mode of its own |
