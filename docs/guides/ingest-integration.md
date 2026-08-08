# Integrating an application with AIR Blackbox ingest

How to make an existing application write tamper-evident, signed receipts for
the decisions it makes about people, when the application itself cannot own
the audit chain.

This is the path a hosted product takes. If you are governing a Claude session
instead, use the MCP tools (`record_action`, `export_evidence`) and stop
reading here.

---

## Why your app should not own the chain

`AuditChain` is a **single-writer** design. Its lock is an in-process
`threading.Lock`, and `resume()` replays the whole history to recover
`prev_hash`. A serverless application violates both assumptions:

- **Ephemeral disk.** Records written to the function's filesystem are gone
  when it freezes.
- **Concurrency.** Two invocations both resume from the same `prev_hash` and
  both claim `chain_seq = N+1`. The chain **forks**.

A forked chain still passes verification. It is internally consistent and
factually wrong, which is worse than a crash, because nothing looks broken
until a regulator runs the verifier.

So the application keeps a durable outbox and POSTs batches to a server that
is the single writer. The application never holds the signing key and cannot
edit what it has already sent. That separation is the point: evidence the
producing system can silently revise is not evidence.

---

## Server setup

Bind one token to one tenant:

```bash
fly secrets set AIR_INGEST_TOKENS="$(openssl rand -hex 32):acme-corp" -a air-mcp
```

Multiple tenants, comma-separated: `"tok1:acme-corp,tok2:globex"`.

The tenant is derived from the **token**, not from the request body. A leaked
token cannot be pointed at another tenant's chain.

> **Never scale this app past one machine.** The write lock is an advisory
> file lock; it serializes writers on one machine and cannot reach across two.
> Two machines with separate volumes do not fork the chain so much as start a
> second one. `fly scale count 1`, and see the comment in `fly.toml`.

Records live on the mounted volume (`AIR_RUNS_DIR=/data/runs`), so they
survive restarts and redeploys.

---

## The wire contract

### `POST /ingest`

```http
POST /ingest
Authorization: Bearer <token>
Content-Type: application/json

{
  "tenant": "acme-corp",
  "events": [
    {
      "event_id": "9ab52593-3f09-4658-aa28-2817ca12f2b1",
      "action": "score_candidate",
      "category": "screening",
      "detail": "cand_4417 scored 0.86 against search criteria",
      "occurred_at": "2026-08-06T18:52:19Z",
      "screening": {
        "decision_type": "score",
        "human_reviewer": "",
        "human_review_required": true,
        "covenant_flags": []
      },
      "attributes": { "user_id": "u_9f3c", "subject_ref": "cand_4417" }
    }
  ]
}
```

Response, in request order:

```json
{"results": [
  {"event_id": "9ab52593-...", "receipt_id": "24f4da9f-...", "chain_hash": "ca494c57..."}
]}
```

A redelivered event returns its **original** `receipt_id` with
`"duplicate": true` and writes nothing.

### Field notes

| Field | Required | Notes |
|---|---|---|
| `event_id` | **yes** | Stable, client-generated, unique per event. The idempotency key. |
| `action` | yes | Short snake_case name. Your vocabulary; the server does not police it. |
| `occurred_at` | recommended | When the decision was **made**. Distinct from when the server wrote it. |
| `category` | optional | Free-form. `screening` marks candidate-affecting decisions. |
| `screening` | optional | Structured block the evidence bundle categorizes on. |
| `attributes` | optional | Passed through uninterpreted. Put your domain nouns here. |

`attributes` is deliberately opaque to the server. Your application's
vocabulary stays yours and never becomes part of this contract.

### Status codes

| Code | Meaning | Client should |
|---|---|---|
| 200 | Written (or recognized as duplicate) | Mark delivered |
| 400 | Malformed payload | **Spend the retry budget.** Retrying cannot fix it. |
| 401 | Bad or missing token | Defer, spend nothing |
| 403 | Token not valid for that tenant | Defer, spend nothing |
| 409 | Another writer holds the chain | Defer, spend nothing |
| 413 | Batch too large (>100) | **Halve the batch and retry.** Events are fine; size is wrong. |
| 503 | Ingest not configured on the server | Defer, spend nothing |

The distinction that matters: only a **malformed payload** should consume a
give-up budget. Everything else is a condition an operator clears, and
stranding compliance evidence because a token was briefly wrong is the wrong
trade. Note that `503` is the *first* response a correctly-built client will
ever see, since the endpoint is inert until its token is set — treating it as
fatal would strand the opening batch.

---

## Client requirements

**1. A durable outbox.** Write the event to your own storage in the same
transaction as the decision. If the outbox insert fails, the decision happened
and no receipt will ever exist for it — there is no queue row, no sequence
gap, nothing to detect later. A missing record is invisible by definition, so
alert loudly on that path. Do **not** fail the user's action; a compliance
pipeline that blocks work teaches everyone to route around it.

**2. A stable `event_id`, written once.** Generate it when the event is
created, store it, never regenerate on retry. `UNIQUE` in your outbox table.
Retries are guaranteed — timeouts, cold starts mid-flush — and without this
key each one appends a phantom record that still verifies clean.

**3. Ordered batches.** Flush as one ordered array, not N sequential requests.
On a partial acknowledgement, mark only what the server confirmed and leave
the rest pending **in order**. Never skip ahead.

**4. Cap your own batches.** Enforce ≤100 events client-side so `413` is
unreachable by construction rather than by coincidence between two codebases.
A coincidence is not a contract.

**5. Instrument decisions, not queries.** Record what affects a person:
scoring, ranking, filtering, rejections, outreach about a specific individual.
Reads that produce no judgment dilute the record an auditor actually reads.

---

## Verifying it works

Chain state for your tenant:

```bash
curl -s https://mcp.airblackbox.ai/ingest/status -H "Authorization: Bearer $TOKEN"
```

```json
{"tenant":"acme-corp","records":3,"ingested_events":3,
 "chain_intact":true,"single_writer":true}
```

Export the signed evidence bundle:

```bash
curl -sO -J https://mcp.airblackbox.ai/ingest/export -H "Authorization: Bearer $TOKEN"
air-evidence verify bundle-*.air-evidence
```

The verifier runs six checks and needs **no secrets** — one public-key
signature covers every file in the bundle. An unreachable timestamp authority
is reported as an anchor **gap**, not a failure: the bundle is honest about
what it could not prove.

Export uses the same token, because that token already owns exactly one
tenant. Note that the MCP `export_evidence` tool exports the *chat session's*
tenant, which is a different tenant from the one your application ingests
under — asking Claude to export will not return these records.

An empty tenant returns `404`, never an empty bundle. A bundle attesting to
nothing still looks like evidence.

---

## What the server does with an event

1. Authenticates the token and resolves its tenant.
2. Validates the **whole batch** before writing any of it, so a malformed tail
   cannot leave a half-written flush to reconcile.
3. Takes the writer lock (threads queue; a competing process gets `409`).
4. For each event: returns the original receipt if `event_id` is known,
   otherwise evaluates the covenant, signs a receipt, and chains the record.

If a covenant is loaded, its verdict is recorded as a **retrospective second
opinion**, never as enforcement. These events already happened inside your
system; the server cannot block the past and does not claim to. An action name
with no matching rule records as `no_rule` rather than the covenant's usual
default-deny, because recording a foreign application's completed action as
"blocked" would fabricate an enforcement event that never occurred — inside a
chain whose entire purpose is not lying.

A real `forbid` rule **is** recorded. "This happened and tenant policy forbids
it" is evidence; "this was blocked" would not be.
