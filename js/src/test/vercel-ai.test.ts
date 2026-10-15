import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";

import { generateText, streamText, tool, wrapLanguageModel } from "ai";
import { MockLanguageModelV4 } from "ai/test";
import { z } from "zod";

import { Covenant } from "../covenant.js";
import { airMiddleware, airTools, CovenantViolation } from "../hooks/vercel-ai.js";
import { record } from "../recorder.js";
import { tmpdir } from "./helpers.js";

function records(dir: string): Array<Record<string, any>> {
  return fs.readdirSync(dir).filter((f) => f.endsWith(".air.json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as Record<string, any>)
    .sort((a, b) => a["chain_seq"] - b["chain_seq"]);
}

const usage = { inputTokens: { total: 12, noCache: 12, cacheRead: 0, cacheWrite: 0 }, outputTokens: { total: 7, text: 7, reasoning: 0 } };

const covenant = Covenant.fromYamlString("agent: a\nrules:\n  - permit: lookupOrder\n  - forbid: issueRefund\n");

function tools() {
  return {
    lookupOrder: tool({
      description: "look up an order",
      inputSchema: z.object({ id: z.string() }),
      execute: async ({ id }) => ({ id, total: 40 }),
    }),
    issueRefund: tool({
      description: "refund an order",
      inputSchema: z.object({ id: z.string(), amount: z.number() }),
      execute: async ({ id, amount }) => `refunded ${amount} on ${id}`,
    }),
  };
}

test("middleware records generate calls with tokens and tool-call names; tools record executions", async () => {
  const dir = tmpdir();
  const rec = record("vercel-agent", { runsDir: dir, anchor: false });
  let call = 0;
  const model = wrapLanguageModel({
    model: new MockLanguageModelV4({
      modelId: "gpt-4o-mini",
      provider: "openai.chat",
      doGenerate: async () => {
        call++;
        if (call === 1) {
          return {
            content: [{ type: "tool-call", toolCallId: "c1", toolName: "lookupOrder", input: JSON.stringify({ id: "991" }) }],
            finishReason: { unified: "tool-calls", raw: "tool_calls" }, usage, warnings: [],
          };
        }
        return { content: [{ type: "text", text: "Order 991 totals $40." }], finishReason: { unified: "stop", raw: "stop" }, usage, warnings: [] };
      },
    }),
    middleware: airMiddleware(rec),
  });
  const result = await generateText({ model, tools: airTools(tools(), rec), prompt: "What did order 991 cost?", stopWhen: ({ steps }) => steps.length >= 2 });
  assert.equal(result.text, "Order 991 totals $40.");

  const recs = records(dir);
  assert.deepEqual(recs.map((r) => r["type"]), ["llm_call", "agent_action", "llm_call"]);
  assert.equal(recs[0]!["framework"], "vercel-ai");
  assert.equal(recs[0]!["model"], "gpt-4o-mini");
  assert.equal(recs[0]!["provider"], "openai.chat");
  assert.deepEqual(recs[0]!["tokens"], { prompt: 12, completion: 7, total: 19 });
  assert.deepEqual(recs[0]!["tool_calls"], ["lookupOrder"]);
  assert.equal(recs[1]!["action"], "lookupOrder");
  assert.equal(recs[1]!["status"], "success");
  assert.equal(recs[1]!["context"]["tool_call_id"], "c1");
  assert.equal(recs[1]!["receipt"]["signing_method"], "ed25519");
  assert.equal(rec.verify().intact, true);
});

test("enforce: a forbidden tool is recorded as blocked and never runs", async () => {
  const dir = tmpdir();
  const rec = record("vercel-agent", { runsDir: dir, anchor: false, covenant });
  let ran = false;
  const t = airTools({
    issueRefund: tool({ inputSchema: z.object({ id: z.string(), amount: z.number() }), execute: async () => { ran = true; return "done"; } }),
  }, rec, { enforce: true });
  await assert.rejects(
    () => (t.issueRefund.execute as (i: unknown, o: unknown) => Promise<unknown>)({ id: "991", amount: 40 }, { toolCallId: "x", messages: [] }),
    (e: unknown) => e instanceof CovenantViolation && e.decision === "forbid",
  );
  assert.equal(ran, false);
  const recs = records(dir);
  assert.equal(recs.length, 1);
  assert.equal(recs[0]!["status"], "blocked");
  assert.equal(recs[0]!["covenant_decision"], "forbid");
  assert.equal(recs[0]!["context"]["blocked_by"], "covenant");

  // Through generateText the violation becomes a tool error the model sees, not a crash.
  const model = wrapLanguageModel({
    model: new MockLanguageModelV4({
      doGenerate: async () => ({
        content: [{ type: "tool-call", toolCallId: "c2", toolName: "issueRefund", input: JSON.stringify({ id: "991", amount: 40 }) }],
        finishReason: { unified: "tool-calls", raw: "tool_calls" }, usage, warnings: [],
      }),
    }),
    middleware: airMiddleware(rec),
  });
  const res = await generateText({ model, tools: airTools(tools(), rec, { enforce: true }), prompt: "refund it" });
  const errPart = res.steps[0]!.content.find((c) => c.type === "tool-error") as { error: unknown } | undefined;
  assert.ok(errPart, "tool error surfaced to the model");
  assert.ok(errPart!.error instanceof CovenantViolation);
  assert.equal(records(dir).filter((r) => r["status"] === "blocked").length, 2);
});

test("without enforce, a forbidden tool runs and the record says so", async () => {
  const dir = tmpdir();
  const rec = record("vercel-agent", { runsDir: dir, anchor: false, covenant });
  const t = airTools(tools(), rec);
  const out = await (t.issueRefund.execute as (i: unknown, o: unknown) => Promise<unknown>)({ id: "991", amount: 40 }, { toolCallId: "x", messages: [] });
  assert.equal(out, "refunded 40 on 991");
  const r = records(dir)[0]!;
  assert.equal(r["status"], "success");
  assert.equal(r["covenant_decision"], "forbid");
});

test("middleware records streamed calls once the stream finishes", async () => {
  const dir = tmpdir();
  const rec = record("vercel-agent", { runsDir: dir, anchor: false });
  const model = wrapLanguageModel({
    model: new MockLanguageModelV4({
      modelId: "claude-sonnet-4-5",
      doStream: async () => ({
        stream: new ReadableStream({
          start(c) {
            c.enqueue({ type: "stream-start", warnings: [] });
            c.enqueue({ type: "text-start", id: "t" });
            c.enqueue({ type: "text-delta", id: "t", delta: "Hello " });
            c.enqueue({ type: "text-delta", id: "t", delta: "world" });
            c.enqueue({ type: "text-end", id: "t" });
            c.enqueue({ type: "finish", finishReason: { unified: "stop", raw: "stop" }, usage });
            c.close();
          },
        }),
      }),
    }),
    middleware: airMiddleware(rec),
  });
  const result = streamText({ model, prompt: "hi" });
  let text = "";
  for await (const chunk of result.textStream) text += chunk;
  assert.equal(text, "Hello world");
  const recs = records(dir);
  assert.equal(recs.length, 1);
  assert.equal(recs[0]!["stream"], true);
  assert.equal(recs[0]!["model"], "claude-sonnet-4-5");
  assert.equal(recs[0]!["provider"], "mock-provider", "the provider the model reports wins over guessing from the name");
  assert.deepEqual(recs[0]!["tokens"], { prompt: 12, completion: 7, total: 19 });
});

test("detailLimit 0 stores only hashes of the tool input", async () => {
  const dir = tmpdir();
  const rec = record("vercel-agent", { runsDir: dir, anchor: false });
  const t = airTools(tools(), rec, { detailLimit: 0 });
  await (t.lookupOrder.execute as (i: unknown, o: unknown) => Promise<unknown>)({ id: "991" }, { toolCallId: "x", messages: [] });
  const r = records(dir)[0]!;
  assert.equal(r["detail"], "");
  assert.match(r["context"]["input_hash"], /^[0-9a-f]{64}$/);
  assert.equal(JSON.stringify(r).includes("991"), false, "the input value appears nowhere in the record");
});

test("a failing tool is recorded as an error", async () => {
  const dir = tmpdir();
  const rec = record("vercel-agent", { runsDir: dir, anchor: false });
  const t = airTools({ boom: tool({ inputSchema: z.object({}), execute: async (): Promise<string> => { throw new Error("kaboom"); } }) }, rec);
  await assert.rejects(() => (t.boom.execute as (i: unknown, o: unknown) => Promise<unknown>)({}, { toolCallId: "x", messages: [] }), /kaboom/);
  const r = records(dir)[0]!;
  assert.equal(r["status"], "error");
  assert.match(r["context"]["error"], /kaboom/);
});
