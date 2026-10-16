import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";

import { tool } from "@langchain/core/tools";
import { FakeListChatModel } from "@langchain/core/utils/testing";
import { z } from "zod";

import { Covenant } from "../covenant.js";
import { AirCallbackHandler, CovenantViolation } from "../hooks/langchain.js";
import { record } from "../recorder.js";
import { tmpdir } from "./helpers.js";

function records(dir: string): Array<Record<string, any>> {
  return fs.readdirSync(dir).filter((f) => f.endsWith(".air.json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as Record<string, any>)
    .sort((a, b) => a["chain_seq"] - b["chain_seq"]);
}

const covenant = Covenant.fromYamlString("agent: a\nrules:\n  - permit: lookup_order\n  - forbid: issue_refund\n");

const lookupOrder = tool(async ({ id }) => ({ id, total: 40 }), { name: "lookup_order", description: "look up", schema: z.object({ id: z.string() }) });
const issueRefund = tool(async ({ id }) => `refunded ${id}`, { name: "issue_refund", description: "refund", schema: z.object({ id: z.string() }) });

test("records chat model calls and tool executions", async () => {
  const dir = tmpdir();
  const rec = record("lc-agent", { runsDir: dir, anchor: false, covenant });
  const handler = new AirCallbackHandler(rec);
  const model = new FakeListChatModel({ responses: ["Order 991 totals $40."] });
  const out = await model.invoke("What did order 991 cost?", { callbacks: [handler] });
  assert.equal(out.content, "Order 991 totals $40.");
  const t = await lookupOrder.invoke({ id: "991" }, { callbacks: [handler] });
  assert.deepEqual(t, { id: "991", total: 40 });
  // Background callbacks: give them a tick.
  await new Promise((r) => setTimeout(r, 50));
  const recs = records(dir);
  assert.deepEqual(recs.map((r) => r["type"]), ["llm_call", "agent_action"]);
  assert.equal(recs[0]!["framework"], "langchain");
  assert.equal(recs[1]!["action"], "lookup_order");
  assert.equal(recs[1]!["status"], "success");
  assert.equal(recs[1]!["covenant_decision"], "permit");
  assert.equal(rec.verify().intact, true);
});

test("enforce: a forbidden tool is stopped before its function runs", async () => {
  const dir = tmpdir();
  const rec = record("lc-agent", { runsDir: dir, anchor: false, covenant });
  const handler = new AirCallbackHandler(rec, { enforce: true });
  let ran = false;
  const refund = tool(async ({ id }) => { ran = true; return `refunded ${id}`; }, { name: "issue_refund", schema: z.object({ id: z.string() }) });
  await assert.rejects(() => refund.invoke({ id: "991" }, { callbacks: [handler] }), (e: unknown) => e instanceof CovenantViolation);
  assert.equal(ran, false);
  const recs = records(dir);
  assert.equal(recs.length, 1);
  assert.equal(recs[0]!["status"], "blocked");
  assert.equal(recs[0]!["action"], "issue_refund");
  // Permitted tools still run under enforce.
  assert.deepEqual(await lookupOrder.invoke({ id: "1" }, { callbacks: [handler] }), { id: "1", total: 40 });
  assert.equal(records(dir).length, 2);
});

test("without enforce the forbidden tool runs and the record carries the decision", async () => {
  const dir = tmpdir();
  const rec = record("lc-agent", { runsDir: dir, anchor: false, covenant });
  const handler = new AirCallbackHandler(rec);
  assert.equal(await issueRefund.invoke({ id: "991" }, { callbacks: [handler] }), "refunded 991");
  await new Promise((r) => setTimeout(r, 50));
  const r = records(dir)[0]!;
  assert.equal(r["status"], "success");
  assert.equal(r["covenant_decision"], "forbid");
});

test("a tool error is recorded as an error", async () => {
  const dir = tmpdir();
  const rec = record("lc-agent", { runsDir: dir, anchor: false });
  const handler = new AirCallbackHandler(rec, { enforce: true });
  const boom = tool(async () => { throw new Error("kaboom"); }, { name: "boom", schema: z.object({}) });
  await assert.rejects(() => boom.invoke({}, { callbacks: [handler] }), /kaboom/);
  const r = records(dir)[0]!;
  assert.equal(r["status"], "error");
  assert.match(r["context"]["error"], /kaboom/);
});

// With prompt caching, Anthropic's raw usage (llmOutput) counts only the
// uncached prompt tokens; LangChain's usage_metadata counts them all.
test("token counts come from usage_metadata, which includes cached prompt tokens", () => {
  const dir = tmpdir();
  const rec = record("lc-agent", { runsDir: dir, anchor: false });
  const handler = new AirCallbackHandler(rec);
  handler.handleChatModelStart({ lc: 1, type: "constructor", id: ["langchain", "chat_models", "anthropic", "ChatAnthropic"], kwargs: { model: "claude-sonnet-4-5" } }, [], "run-1");
  handler.handleLLMEnd({
    generations: [[{ text: "", message: { usage_metadata: { input_tokens: 47, output_tokens: 17, total_tokens: 64, input_token_details: { cache_read: 5 } } } } as never]],
    llmOutput: { usage: { input_tokens: 42, output_tokens: 17, cache_creation_input_tokens: 0, cache_read_input_tokens: 5 } },
  }, "run-1");
  assert.deepEqual(records(dir)[0]!["tokens"], { prompt: 47, completion: 17, total: 64 });
});
