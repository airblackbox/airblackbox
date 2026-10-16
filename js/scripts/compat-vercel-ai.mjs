// AI SDK 5 (provider v2) and 6 (provider v3): same checks as the v7 test.
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { generateText, streamText, tool, wrapLanguageModel } from "ai";
import * as testing from "ai/test";
import { z } from "zod";
const { record, Covenant } = await import(path.resolve("dist/index.js"));
const { airMiddleware, airTools, CovenantViolation } = await import(path.resolve("dist/hooks/vercel-ai.js"));

const v2 = !!testing.MockLanguageModelV2 && !testing.MockLanguageModelV3;
const Mock = testing.MockLanguageModelV3 ?? testing.MockLanguageModelV2;
const usage = v2 ? { inputTokens: 12, outputTokens: 7, totalTokens: 19 }
  : { inputTokens: { total: 12, noCache: 12, cacheRead: 0, cacheWrite: 0 }, outputTokens: { total: 7, text: 7, reasoning: 0 } };
const fr = (r) => (v2 ? r : { unified: r, raw: r });
const recs = (d) => fs.readdirSync(d).filter((f) => f.endsWith(".air.json"))
  .map((f) => JSON.parse(fs.readFileSync(path.join(d, f), "utf8"))).sort((a, b) => a.chain_seq - b.chain_seq);
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "compat-"));

// generate + tool loop
{
  const dir = tmp();
  const rec = record("v", { runsDir: dir, anchor: false });
  let call = 0;
  const model = wrapLanguageModel({
    model: new Mock({ modelId: "gpt-4o-mini", doGenerate: async () => (++call === 1
      ? { content: [{ type: "tool-call", toolCallId: "c1", toolName: "lookupOrder", input: JSON.stringify({ id: "991" }) }], finishReason: fr("tool-calls"), usage, warnings: [] }
      : { content: [{ type: "text", text: "Order 991 totals $40." }], finishReason: fr("stop"), usage, warnings: [] }) }),
    middleware: airMiddleware(rec),
  });
  const tools = airTools({ lookupOrder: tool({ inputSchema: z.object({ id: z.string() }), execute: async ({ id }) => ({ id, total: 40 }) }) }, rec);
  const r = await generateText({ model, tools, prompt: "cost?", stopWhen: ({ steps }) => steps.length >= 2 });
  assert.equal(r.text, "Order 991 totals $40.");
  const rs = recs(dir);
  assert.deepEqual(rs.map((x) => x.type), ["llm_call", "agent_action", "llm_call"]);
  assert.deepEqual(rs[0].tokens, { prompt: 12, completion: 7, total: 19 });
  assert.deepEqual(rs[0].tool_calls, ["lookupOrder"]);
  assert.equal(rs[1].action, "lookupOrder");
  assert.equal(rec.verify().intact, true);
}
// stream
{
  const dir = tmp();
  const rec = record("v", { runsDir: dir, anchor: false });
  const model = wrapLanguageModel({
    model: new Mock({ modelId: "m", doStream: async () => ({ stream: new ReadableStream({ start(c) {
      c.enqueue({ type: "stream-start", warnings: [] });
      c.enqueue({ type: "text-start", id: "t" });
      c.enqueue({ type: "text-delta", id: "t", delta: "Hello" });
      c.enqueue({ type: "text-end", id: "t" });
      c.enqueue({ type: "finish", finishReason: fr("stop"), usage });
      c.close();
    } }) }) }),
    middleware: airMiddleware(rec),
  });
  let text = "";
  for await (const t of streamText({ model, prompt: "hi" }).textStream) text += t;
  assert.equal(text, "Hello");
  const rs = recs(dir);
  assert.equal(rs.length, 1);
  assert.equal(rs[0].stream, true);
  assert.deepEqual(rs[0].tokens, { prompt: 12, completion: 7, total: 19 });
}
// enforce
{
  const dir = tmp();
  const rec = record("v", { runsDir: dir, anchor: false, covenant: Covenant.fromYamlString("agent: a\nrules:\n  - forbid: issueRefund\n") });
  let ran = false;
  const t = airTools({ issueRefund: tool({ inputSchema: z.object({ id: z.string() }), execute: async () => { ran = true; return "x"; } }) }, rec, { enforce: true });
  await assert.rejects(() => t.issueRefund.execute({ id: "1" }, { toolCallId: "x", messages: [] }), (e) => e instanceof CovenantViolation);
  assert.equal(ran, false);
  assert.equal(recs(dir)[0].status, "blocked");
}
console.log(`ok: ai ${JSON.parse(fs.readFileSync("node_modules/ai/package.json")).version} (provider ${v2 ? "v2" : "v3"})`);
