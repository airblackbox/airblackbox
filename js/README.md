# air-blackbox (TypeScript)

Record what a TypeScript AI agent does into a signed, tamper-evident chain
that anyone can verify, and stop the actions its policy forbids before they
run.

This is the TypeScript side of [AIR Blackbox](https://github.com/airblackbox/airblackbox).
It writes the same records, receipts and `.air-evidence` bundles as the
Python SDK, byte for byte. The Python verifier (`air-blackbox verify`) and the
browser verifier at <https://airblackbox.ai/verify> read bundles from either
language, and a Node process and a Python process can take turns writing one
chain.

```bash
npm install air-blackbox
```

Node 20 or later. Signing keys are generated in your process and never leave
your machine. There is no account, no API key and no hosted service.

## Record actions

```ts
import { record } from "air-blackbox";

const rec = record("support-agent");
rec.action("read_ticket", "ticket #4821");
rec.action("issue_refund", "order 991, $40", { humanReviewer: "dana@acme.example" });

const bundle = await rec.export();   // drop it on https://airblackbox.ai/verify
console.log(rec.fingerprint);       // ed25519:...  give this to whoever verifies
```

Each action is chained (HMAC-SHA256) and individually signed (Ed25519). On
export the chain head is timestamped by a public RFC 3161 authority when one
is reachable. That timestamp is what lets a verifier detect a history the
operator rewrote and re-signed after the fact. An unreachable authority is
recorded in the bundle as a gap, never hidden.

## Hook into your framework

Each hook records model calls and tool executions automatically. Where the
framework lets a hook sit in front of the tool, `enforce: true` also stops a
tool the covenant does not permit: the attempt is recorded as blocked and the
tool body never runs.

| Framework | Import | Records | Can block a tool |
|---|---|---|---|
| Vercel AI SDK 5+ | `air-blackbox/vercel-ai` | model calls (incl. streaming), tool executions | yes |
| OpenAI Agents SDK 0.17+ | `air-blackbox/openai-agents` | tool executions, model calls, handoffs, guardrails, agent runs | yes, per tool with `airTool` |
| LangChain.js / LangGraph.js (core 0.3+) | `air-blackbox/langchain` | model calls, tool executions | yes |
| MCP TypeScript SDK 1.x | `air-blackbox/mcp` | every `callTool` | yes |

### Vercel AI SDK

```ts
import { generateText, wrapLanguageModel } from "ai";
import { openai } from "@ai-sdk/openai";
import { record } from "air-blackbox";
import { airMiddleware, airTools } from "air-blackbox/vercel-ai";

const rec = record("support-agent", { covenant: "covenant.yaml" });
const model = wrapLanguageModel({ model: openai("gpt-4o"), middleware: airMiddleware(rec) });
const tools = airTools({ lookupOrder, issueRefund }, rec, { enforce: true });

await generateText({ model, tools, prompt: "Refund order 991" });
await rec.export();
```

A blocked tool throws `CovenantViolation`, which the SDK hands back to the
model as a tool error, so the model can explain instead of the run crashing.

### OpenAI Agents SDK

```ts
import { Agent, run, tool } from "@openai/agents";
import { record } from "air-blackbox";
import { installAirTracing, airTool } from "air-blackbox/openai-agents";

const rec = record("triage-agent", { covenant: "covenant.yaml" });
await installAirTracing(rec);

const issueRefund = tool({
  name: "issue_refund",
  parameters: z.object({ id: z.string() }),
  execute: airTool("issue_refund", rec, async ({ id }) => refund(id)),
});
await run(new Agent({ name: "support", tools: [issueRefund] }), "Refund order 991");
```

The tracing processor observes after the fact, so on its own it records a
forbidden tool as having run against policy. Wrap a tool's `execute` with
`airTool` to stop it beforehand. The processor reads tool arguments from the
SDK's spans, which carry them by default; if you set
`traceIncludeSensitiveData: false`, records keep tool names and outcomes but
covenant rules that test argument values cannot see them. The SDK disables
tracing when `NODE_ENV=test` unless you call `setTracingDisabled(false)`.

### LangChain.js and LangGraph.js

```ts
import { AirCallbackHandler } from "air-blackbox/langchain";

const handler = new AirCallbackHandler(rec, { enforce: true });
await agent.invoke(input, { callbacks: [handler] });
```

With `enforce`, LangChain awaits the handler before each tool and propagates
the `CovenantViolation` it throws, so the tool function is never called.
LangChain logs the violation as a handler error; that log line is expected.

### MCP

```ts
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { airMcpClient } from "air-blackbox/mcp";

const client = airMcpClient(new Client({ name: "agent", version: "1.0" }), rec, { enforce: true });
await client.connect(transport);
await client.callTool({ name: "send_email", arguments: { to: "..." } });  // blocked if forbidden
```

## Covenants and the gate

A covenant is the policy the agent commits to before it acts. It is the same
YAML as the Python SDK and produces the same hash, so a receipt proves which
rules were active whichever language enforced them.

```yaml
agent: support-agent
rules:
  - permit: lookup_order
  - require_approval: issue_refund
    when: "amount > 100"
  - permit: issue_refund
    when: "amount <= 100"
  - forbid: delete_records
```

Precedence is forbid, then require_approval, then permit, and anything not
named is forbidden. A guard that cannot be evaluated (a missing field, a
non-number compared with `>`) never grants and never lifts a forbid.

For two-phase receipts (authorize, then seal with the result), use the gate
directly:

```ts
import { Gate, Covenant } from "air-blackbox";

const gate = new Gate({ covenant: Covenant.fromYaml("covenant.yaml"), onApprovalNeeded: askAHuman });
const receipt = await gate.authorizeAsync({ agentId: "support-agent", actionName: "issue_refund",
                                            payload: { order: 991, amount: 140 }, context: { amount: 140 } });
if (receipt.authorized) {
  const result = await refund(991);
  gate.seal(receipt, { result, status: "success" });
}
```

## What it records, and what it does not

- Tool outputs are stored only as a SHA-256 hash. Tool inputs are stored as
  a hash plus the first 500 characters in the record's `detail`, for
  readability; pass `detailLimit: 0` to a hook to store only the hash. Model
  calls record the model, provider, token counts, duration and the names of
  tools the model asked for, never the prompt or the completion.
- A hook sees what its framework reports. Side effects a tool causes outside
  the framework's tool call (a background job it starts, a process it shells
  out to) are not visible to any hook.
- Signatures are Ed25519. The Python SDK can also sign with ML-DSA-65
  (post-quantum); this package reports such receipts as not checkable here
  rather than as invalid. Verify them with the Python SDK.
- The chain has one writer at a time. Several processes sharing one history
  should use the ingest server instead (see the main repository).

## Tested against

The suite runs the hooks through each framework's real execution path (the
AI SDK's `generateText` and `streamText`, an Agents SDK `run()` with its
scripted model, LangChain's tool invocation, an MCP client and server over an
in-memory transport). Differential tests check that the Python SDK verifies
this package's chains, receipts and bundles, that this package verifies the
Python SDK's, and that the two can share one chain.

| Package | Versions exercised |
|---|---|
| `ai` | 5.0, 6.0, 7.0 |
| `@openai/agents` | 0.17, 0.20 |
| `@langchain/core` | 0.3, 1.2 |
| `@modelcontextprotocol/sdk` | 1.32 |

## License

Apache-2.0.
