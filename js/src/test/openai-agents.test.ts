import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";

import {
  createFunctionSpan, createGenerationSpan, createHandoffSpan, createGuardrailSpan, setTraceProcessors, setTracingDisabled, withTrace,
} from "@openai/agents";

import { Covenant } from "../covenant.js";
import { AirTraceProcessor, airTool, CovenantViolation } from "../hooks/openai-agents.js";
import { record } from "../recorder.js";
import { tmpdir } from "./helpers.js";

function records(dir: string): Array<Record<string, any>> {
  return fs.readdirSync(dir).filter((f) => f.endsWith(".air.json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as Record<string, any>)
    .sort((a, b) => a["chain_seq"] - b["chain_seq"]);
}

test("the processor records function, generation, handoff and guardrail spans", async () => {
  const dir = tmpdir();
  const rec = record("agents-sdk", { runsDir: dir, anchor: false, covenant: Covenant.fromYamlString("agent: a\nrules:\n  - permit: lookup_order\n") });
  const processor = new AirTraceProcessor(rec);
  setTracingDisabled(false);
  setTraceProcessors([processor]);

  await withTrace("test run", async (trace) => {
    const gen = createGenerationSpan({ data: { model: "gpt-4.1", usage: { input_tokens: 20, output_tokens: 9 }, output: [{ type: "function_call", name: "lookup_order" }] } }, trace);
    gen.start();
    gen.end();
    const fn = createFunctionSpan({ data: { name: "lookup_order", input: JSON.stringify({ id: "991" }), output: JSON.stringify({ total: 40 }) } }, trace);
    fn.start();
    fn.end();
    const bad = createFunctionSpan({ data: { name: "delete_records", input: "{}", output: "" } }, trace);
    bad.start();
    bad.setError({ message: "disk on fire" });
    bad.end();
    const h = createHandoffSpan({ data: { from_agent: "triage", to_agent: "refunds" } }, trace);
    h.start();
    h.end();
    const g = createGuardrailSpan({ data: { name: "pii", triggered: true } }, trace);
    g.start();
    g.end();
  });
  await processor.forceFlush();

  const recs = records(dir);
  assert.deepEqual(recs.map((r) => r["type"]), ["llm_call", "agent_action", "agent_action", "handoff", "guardrail"]);
  assert.equal(recs[0]!["model"], "gpt-4.1");
  assert.deepEqual(recs[0]!["tokens"], { prompt: 20, completion: 9, total: 29 });
  assert.deepEqual(recs[0]!["tool_calls"], ["lookup_order"]);
  assert.equal(recs[1]!["action"], "lookup_order");
  assert.equal(recs[1]!["covenant_decision"], "permit");
  assert.equal(recs[1]!["status"], "success");
  assert.equal(recs[2]!["action"], "delete_records");
  assert.equal(recs[2]!["status"], "error");
  assert.equal(recs[2]!["covenant_decision"], "forbid", "ran against policy, and the record says so");
  assert.equal(recs[3]!["to_agent"], "refunds");
  assert.equal(recs[4]!["triggered"], true);
  assert.equal(rec.verify().intact, true);
  setTraceProcessors([]);
});

test("a real run(): tool executions and model calls land in the chain; airTool blocks a forbidden one", async () => {
  const { Agent, run, tool } = await import("@openai/agents");
  const { ScriptedModel, functionCall, assistantMessage } = await import("@openai/agents/testing");
  const { z } = await import("zod");
  const dir = tmpdir();
  const rec = record("agents-sdk", {
    runsDir: dir, anchor: false,
    covenant: Covenant.fromYamlString("agent: a\nrules:\n  - permit: lookup_order\n  - forbid: issue_refund\n"),
  });
  const processor = new AirTraceProcessor(rec);
  setTracingDisabled(false);
  setTraceProcessors([processor]);
  let refunded = false;
  const lookupOrder = tool({
    name: "lookup_order", description: "look up", parameters: z.object({ id: z.string() }),
    execute: async ({ id }) => JSON.stringify({ id, total: 40 }),
  });
  const issueRefund = tool({
    name: "issue_refund", description: "refund", parameters: z.object({ id: z.string() }),
    execute: airTool("issue_refund", rec, async ({ id }: { id: string }) => { refunded = true; return `refunded ${id}`; }),
  });
  const model = new ScriptedModel([
    [functionCall("lookup_order", { id: "991" }, { callId: "c1" })],
    [functionCall("issue_refund", { id: "991" }, { callId: "c2" })],
    [assistantMessage("I could not issue that refund.")],
  ]);
  const agent = new Agent({ name: "support", instructions: "help", model, tools: [lookupOrder, issueRefund] });
  const result = await run(agent, "refund order 991");
  await processor.forceFlush();
  setTraceProcessors([]);
  assert.equal(result.finalOutput, "I could not issue that refund.");
  assert.equal(refunded, false, "the forbidden tool body never ran");

  const recs = records(dir);
  const actions = recs.filter((r) => r["type"] === "agent_action");
  const lookup = actions.find((r) => r["action"] === "lookup_order" && r["status"] === "success")!;
  assert.ok(lookup, "the permitted tool's execution is recorded");
  assert.equal(lookup["covenant_decision"], "permit");
  assert.ok(lookup["context"]["input_hash"], "tool arguments reach the processor (SDK default traceIncludeSensitiveData)");
  assert.ok(actions.some((r) => r["action"] === "issue_refund" && r["status"] === "blocked"), "the blocked attempt is recorded");
  assert.ok(recs.some((r) => r["type"] === "agent_run" && r["agent"] === "support"));
  assert.equal(rec.verify().intact, true);
});

test("airTool enforces the covenant before the tool body runs", () => {
  const dir = tmpdir();
  const rec = record("agents-sdk", { runsDir: dir, anchor: false, covenant: Covenant.fromYamlString("agent: a\nrules:\n  - permit: lookup_order\n") });
  let ran = false;
  const ok = airTool("lookup_order", rec, async (_args: { id: string }) => { ran = true; return "x"; });
  const forbidden = airTool("delete_records", rec, async () => { ran = true; return "x"; });
  assert.doesNotThrow(() => ok({ id: "1" }));
  assert.throws(() => forbidden(), (e: unknown) => e instanceof CovenantViolation);
  const recs = records(dir);
  assert.equal(recs.length, 1, "only the blocked attempt is recorded here; the processor records executions");
  assert.equal(recs[0]!["status"], "blocked");
  assert.equal(ran, true);
});
