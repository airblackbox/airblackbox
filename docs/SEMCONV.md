# OpenTelemetry GenAI Semantic Conventions Alignment

AIR Blackbox Gateway emits spans aligned with the OpenTelemetry GenAI
semantic conventions. This document records the mapping, the dual-emission
transition policy, and what changes for downstream queries.

Status of the upstream conventions: Development (not yet stable). The
upstream transition mechanism is the `OTEL_SEMCONV_STABILITY_OPT_IN`
environment variable; until the conventions stabilize, this gateway
dual-emits old and new attribute names so no downstream dashboard breaks.

## Attribute mapping

| Old (deprecated, still emitted) | New (semconv / air namespace) | Notes |
|---|---|---|
| `gen_ai.system` | `gen_ai.provider.name` | Semconv renamed the provider discriminator |
| `gen_ai.usage.prompt_tokens` | `gen_ai.usage.input_tokens` | Includes cached tokens per spec |
| `gen_ai.usage.completion_tokens` | `gen_ai.usage.output_tokens` | |
| `gen_ai.run.id` | `air.run.id` | Vendor attribute, moved out of the `gen_ai.*` namespace |
| `gen_ai.request.endpoint` | `air.request.endpoint` | Vendor attribute, moved out of the `gen_ai.*` namespace |
| span name `llm.call` | `chat {gen_ai.request.model}` (e.g. `chat gpt-4o`) | Semconv span naming for inference spans |
| (new) | `gen_ai.operation.name` = `chat` | Required by semconv span naming |

Unchanged and already spec-aligned: `gen_ai.request.model`,
`gen_ai.response.model`.

Kept as vendor attributes (no semconv equivalent): `gen_ai.duration_ms`
(semconv models duration as the `gen_ai.client.operation.duration` metric;
the span attribute remains for query convenience), `gen_ai.stream`.

## Breaking change to watch

The span name changed from `llm.call` to `chat {model}`. Any saved Jaeger
queries or alerting rules that match the literal span name `llm.call` must
be updated to match `chat *` or filter on `gen_ai.operation.name = chat`.

## Deprecation timeline

- Current release: dual-emission. Old and new names both present.
- Next minor release: deprecated names removed. Migrate queries to the new
  names before upgrading.

## Why this matters

The gen_ai.* conventions are the emerging standard schema for AI telemetry.
Emitting them means any OTel-native backend (Jaeger, Grafana, Datadog,
anything) renders AIR Blackbox traces with the same fidelity as traces from
official SDK instrumentations, and positions the gateway's audit attributes
as a clean vendor extension (`air.*`) on top of the standard rather than a
fork of it.
