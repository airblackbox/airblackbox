// What a stress and tamper test of the packed package found. Each case
// failed before the fix it covers.
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as http from "node:http";
import * as path from "node:path";
import { inspect } from "node:util";
import { test } from "node:test";

import { tool as lcTool } from "@langchain/core/tools";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { tool } from "ai";
import { z } from "zod";

import { checkResponse, makeQuery, timestampHead } from "../anchor.js";
import { parsePreserving, pythonJson } from "../canonical.js";
import { AuditChain, verifyChain } from "../chain.js";
import { Covenant } from "../covenant.js";
import { AirCallbackHandler } from "../hooks/langchain.js";
import { airMcpClient } from "../hooks/mcp.js";
import { airTools } from "../hooks/vercel-ai.js";
import { hashPayload } from "../receipt.js";
import { record } from "../recorder.js";
import { hasAirSdk, python, tmpdir } from "./helpers.js";

function records(dir: string): Array<Record<string, any>> {
  return fs.readdirSync(dir).filter((f) => f.endsWith(".air.json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as Record<string, any>)
    .sort((a, b) => a["chain_seq"] - b["chain_seq"]);
}

const call = { toolCallId: "c1", messages: [] };
type Exec = (input: unknown, opts: unknown) => Promise<unknown>;

// --- Recording must never break the agent's own work ----------------------

test("a tool output that cannot be serialised is still returned, and the call is recorded", async () => {
  const dir = tmpdir();
  const errors: unknown[] = [];
  const rec = record("agent", { runsDir: dir, anchor: false, onRecordError: (e) => errors.push(e) });
  const circular: Record<string, unknown> = { total: 40 };
  circular["self"] = circular;
  const outputs: unknown[] = [circular, { n: NaN, f: () => 1, big: 10n ** 30n }, new Map([["a", 1]])];
  for (const out of outputs) {
    const t = airTools({ lookup: tool({ inputSchema: z.object({ id: z.string() }), execute: async () => out }) }, rec, { enforce: true });
    assert.equal(await (t.lookup.execute as Exec)({ id: "A-1" }, call), out, "the tool's result reaches the agent unchanged");
  }
  const recs = records(dir);
  assert.equal(recs.length, 3);
  assert.ok(recs.every((r) => r["status"] === "success" && /^[0-9a-f]{64}$/.test(r["context"]["output_hash"])));
  assert.equal(errors.length, 0, "these are hashed, not reported as failures");
  assert.equal(rec.verify().intact, true);
});

test("a runs directory that cannot be written reaches onRecordError, not the agent", async () => {
  const dir = tmpdir();
  const errors: unknown[] = [];
  const rec = record("agent", { runsDir: dir, anchor: false, onRecordError: (e) => errors.push(e) });
  let ran = 0;
  const tools = airTools({ refund: tool({ inputSchema: z.object({ id: z.string() }), execute: async () => { ran++; return "refunded"; } }) }, rec);
  // The directory replaced by a file: every write fails, even as root.
  fs.rmSync(dir, { recursive: true, force: true });
  fs.writeFileSync(dir, "not a directory");
  assert.equal(await (tools.refund.execute as Exec)({ id: "A-1" }, call), "refunded");
  assert.equal(ran, 1, "ran once: the agent saw success, so a retrying model has no reason to run it again");
  assert.equal(errors.length, 1);
  assert.equal(rec.recordErrors, 1);
});

test("a streaming tool the consumer stops early is still recorded", async () => {
  const dir = tmpdir();
  const rec = record("agent", { runsDir: dir, anchor: false });
  const t = airTools({
    feed: tool({ inputSchema: z.object({}), execute: async function* () { for (let i = 0; i < 10; i++) yield i; } }),
  }, rec);
  const stream = (await (t.feed.execute as Exec)({}, call)) as AsyncIterable<number>;
  for await (const n of stream) if (n === 2) break;
  const recs = records(dir);
  assert.equal(recs.length, 1);
  assert.equal(recs[0]!["status"], "error");
  assert.match(recs[0]!["context"]["error"], /consumer ended the stream/);
});

// --- Model-written arguments cannot satisfy app-only guards ---------------

const GUARDED = Covenant.fromYamlString(
  "agent: a\nrules:\n  - forbid: send_email\n    unless: human_approved\n  - permit: send_email\n  - permit: read_docs\n    category: read_only\n",
);

test("MCP: an argument named human_approved does not lift a forbid, nor does category grant", async () => {
  const dir = tmpdir();
  const rec = record("agent", { runsDir: dir, anchor: false, covenant: GUARDED });
  const executed: string[] = [];
  const server = new McpServer({ name: "s", version: "1.0.0" });
  server.registerTool("send_email", { inputSchema: { to: z.string(), human_approved: z.unknown().optional() } }, async () => {
    executed.push("send_email");
    return { content: [{ type: "text", text: "sent" }] };
  });
  server.registerTool("delete_records", { inputSchema: { category: z.string().optional() } }, async () => {
    executed.push("delete_records");
    return { content: [{ type: "text", text: "deleted" }] };
  });
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = airMcpClient(new Client({ name: "agent", version: "1.0.0" }), rec, { enforce: true });
  await client.connect(ct);
  await assert.rejects(client.callTool({ name: "send_email", arguments: { to: "robin@example.com", human_approved: true } }));
  await assert.rejects(client.callTool({ name: "delete_records", arguments: { category: "read_only" } }));
  assert.deepEqual(executed, []);
  assert.deepEqual(records(dir).map((r) => [r["action"], r["covenant_decision"]]), [["send_email", "forbid"], ["delete_records", "forbid"]]);
});

test("LangChain: arguments outside the tool's schema cannot lift a forbid either", async () => {
  const dir = tmpdir();
  const rec = record("agent", { runsDir: dir, anchor: false, covenant: GUARDED });
  let sent = false;
  const sendEmail = lcTool(async () => { sent = true; return "sent"; }, { name: "send_email", description: "send", schema: z.object({ to: z.string() }) });
  await assert.rejects(sendEmail.invoke({ to: "robin@example.com", human_approved: true } as never, { callbacks: [new AirCallbackHandler(rec, { enforce: true })] }));
  assert.equal(sent, false);
});

test("Vercel: a loose schema passes human_approved through, and it still does not count", async () => {
  const dir = tmpdir();
  const rec = record("agent", { runsDir: dir, anchor: false, covenant: GUARDED });
  let sent = false;
  const t = airTools({ send_email: tool({ inputSchema: z.looseObject({ to: z.string() }), execute: async () => { sent = true; return "sent"; } }) }, rec, { enforce: true });
  await assert.rejects((t.send_email.execute as Exec)({ to: "robin@example.com", human_approved: true }, call));
  assert.equal(sent, false);
});

test("the application can still supply a guard through recorder.action", () => {
  const rec = record("agent", { runsDir: tmpdir(), anchor: false, covenant: GUARDED });
  assert.equal(rec.action("send_email", "welcome", { guard: { human_approved: true } }).decision, "permit");
});

// --- The chain on disk ---------------------------------------------------

test("a __proto__ key survives the round trip, so the chain still verifies and resumes", () => {
  const dir = tmpdir();
  const ctx = JSON.parse('{"__proto__": {"admin": true}, "event": "webhook"}') as Record<string, unknown>;
  record("agent", { runsDir: dir, anchor: false }).action("ingest", "webhook", { context: ctx });
  const parsed = parsePreserving('{"__proto__": {"admin": true}}') as Record<string, unknown>;
  assert.ok(Object.prototype.hasOwnProperty.call(parsed, "__proto__"));
  assert.equal(pythonJson(parsed), '{"__proto__": {"admin": true}}');
  const chain = new AuditChain(dir, undefined, true);
  chain.write({ type: "next" });
  assert.equal(verifyChain(dir).intact, true);
});

test("a record field named run_id cannot choose the record's file", () => {
  const dir = path.join(tmpdir(), "runs"); // a parent no other test shares
  const rec = record("agent", { runsDir: dir, anchor: false });
  rec.observe("llm_call", { run_id: "../escaped", model: "gpt-4o" });
  assert.equal(fs.existsSync(path.join(dir, "..", "escaped.air.json")), false);
  assert.equal(records(dir).length, 1);
  assert.throws(() => new AuditChain(dir).write({ run_id: "../x" }), /not a safe file name/);
});

test("a value that reads differently each time cannot split a record from its hash", () => {
  const dir = tmpdir();
  let n = 0;
  const ctx = { get flaky() { return ++n; } };
  record("agent", { runsDir: dir, anchor: false }).action("x", "y", { context: ctx as never });
  assert.equal(verifyChain(dir).intact, true);
});

test("differential: a Python record holding NaN does not break the chain when Node resumes it", { skip: !hasAirSdk() && "air_blackbox SDK not importable" }, () => {
  const dir = tmpdir();
  python(`
from air_blackbox.trust.chain import AuditChain
AuditChain(runs_dir=${JSON.stringify(dir)}).write({"type": "metric", "score": float("nan"), "peak": float("inf")})
`);
  const rec = record("agent", { runsDir: dir, anchor: false });
  rec.action("after_python", "x");
  assert.equal(rec.verify().intact, true);
  // Python recomputes every hash itself, NaN and all.
  const out = python(`
import glob, hashlib, hmac, json
recs = [json.load(open(p)) for p in glob.glob(${JSON.stringify(dir)} + "/*.air.json")]
recs.sort(key=lambda r: (r.get("chain_seq") or 0, r.get("timestamp") or ""))
prev = b"genesis"; ok = True
for r in recs:
    clean = {k: v for k, v in r.items() if k != "chain_hash"}
    h = hmac.new(b"air-blackbox-default", prev + json.dumps(clean, sort_keys=True).encode(), hashlib.sha256)
    ok = ok and h.hexdigest() == r["chain_hash"]; prev = h.digest()
print(json.dumps({"ok": ok, "n": len(recs)}))`);
  assert.deepEqual(JSON.parse(out), { ok: true, n: 2 });
});

test("an export says the chain is not intact when a written record is gone or unreadable", async () => {
  for (const damage of ["delete", "corrupt"] as const) {
    const dir = tmpdir();
    const rec = record("agent", { runsDir: dir, anchor: false });
    rec.action("a", "1");
    rec.action("b", "2");
    const last = records(dir).at(-1)!;
    const file = path.join(dir, `${last["run_id"]}.air.json`);
    if (damage === "delete") fs.rmSync(file);
    else fs.writeFileSync(file, "{ torn");
    const original = console.warn;
    console.warn = () => {};
    try {
      await rec.export();
    } finally {
      console.warn = original;
    }
    assert.match(rec.lastExportNote, /chain not intact/, damage);
  }
});

// --- Writers ---------------------------------------------------------------

test("two recorders on one directory in one process append to one chain", () => {
  const dir = tmpdir();
  const a = record("agent", { runsDir: dir, anchor: false });
  const b = record("agent", { runsDir: dir, anchor: false });
  for (let i = 0; i < 5; i++) {
    a.action("from_a", String(i));
    b.action("from_b", String(i));
  }
  assert.equal(a.verify().intact, true);
  assert.deepEqual(records(dir).map((r) => r["chain_seq"]), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
});

const recorderModule = new URL("../recorder.js", import.meta.url).href;

test("a second process is refused while this one is recording, and allowed once it has exited", () => {
  const dir = tmpdir();
  record("agent", { runsDir: dir, anchor: false }).action("x", "y");
  const other = spawnSync(process.execPath, ["--input-type=module", "-e",
    `import { record } from ${JSON.stringify(recorderModule)}; record("agent", { runsDir: ${JSON.stringify(dir)}, anchor: false });`], { encoding: "utf8" });
  assert.notEqual(other.status, 0);
  assert.match(other.stderr, /is being recorded by process/);

  // Once this process closes its recorder, the other may continue the chain.
  const rec = record("agent", { runsDir: dir, anchor: false });
  rec.close();
  for (const r of [rec]) assert.throws(() => r.action("late", "x"), /closed/);
  // Every recorder on the directory in this process must close first: the
  // one from the first line above is still open.
  assert.notEqual(spawnSync(process.execPath, ["--input-type=module", "-e",
    `import { record } from ${JSON.stringify(recorderModule)}; record("agent", { runsDir: ${JSON.stringify(dir)}, anchor: false });`]).status, 0);

  // A lock left by a process that has exited is taken over.
  const dir2 = tmpdir();
  const first = spawnSync(process.execPath, ["--input-type=module", "-e",
    `import { record } from ${JSON.stringify(recorderModule)}; record("agent", { runsDir: ${JSON.stringify(dir2)}, anchor: false }).action("x", "y"); process.kill(process.pid, "SIGKILL");`], { encoding: "utf8" });
  assert.equal(first.signal, "SIGKILL");
  assert.ok(fs.existsSync(path.join(dir2, ".air-writer.lock")), "a killed process leaves its lock behind");
  record("agent", { runsDir: dir2, anchor: false }).action("after", "restart");
  assert.equal(verifyChain(dir2).intact, true);
});

test("closing hands the directory to another process, which continues the chain", () => {
  const dir = tmpdir();
  const rec = record("agent", { runsDir: dir, anchor: false });
  rec.action("parent", "1");
  rec.close();
  const child = spawnSync(process.execPath, ["--input-type=module", "-e",
    `import { record } from ${JSON.stringify(recorderModule)}; record("agent", { runsDir: ${JSON.stringify(dir)}, anchor: false }).action("child", "2");`], { encoding: "utf8" });
  assert.equal(child.status, 0, child.stderr);
  const again = record("agent", { runsDir: dir, anchor: false });
  again.action("parent", "3");
  assert.deepEqual(records(dir).map((r) => r["action"]), ["parent", "child", "parent"]);
  assert.equal(again.verify().intact, true);
  again.close();
});

test("processes starting at once on a fresh directory agree on one signing key", async () => {
  const dir = tmpdir();
  const script = `import { Recorder } from ${JSON.stringify(recorderModule)};
try { console.log(new Recorder("agent", { runsDir: ${JSON.stringify(dir)}, anchor: false }).fingerprint); }
catch (e) { console.log(/being recorded/.test(e.message) ? "locked" : "ERROR " + e.message); }`;
  const outcomes = await Promise.all(Array.from({ length: 12 }, () => new Promise<string>((resolve) => {
    const child = spawn(process.execPath, ["--input-type=module", "-e", script]);
    let out = "";
    child.stdout.on("data", (b: Buffer) => (out += b));
    child.on("close", () => resolve(out.trim()));
  })));
  assert.ok(outcomes.every((o) => o === "locked" || o.startsWith("ed25519:")), outcomes.join(" | "));
  const keys = new Set(outcomes.filter((o) => o.startsWith("ed25519:")));
  assert.ok(keys.size <= 1, `one identity, got ${[...keys].join(", ")}`);
});

test("a recorder name with a slash still exports, into the directory asked for", async () => {
  const dir = tmpdir();
  const out = tmpdir();
  const rec = record("acme/support", { runsDir: dir, anchor: false });
  rec.action("x", "y");
  const bundle = await rec.export(out);
  assert.equal(path.dirname(bundle), out);
  assert.match(path.basename(bundle), /^bundle-.*-acme_support-[0-9a-f]{8}\.air-evidence$/);
});

test("console.log of a recorder does not print its HMAC key", () => {
  const rec = record("agent", { runsDir: tmpdir(), anchor: false, hmacKey: "SECRET-HMAC-KEY-VALUE" });
  assert.equal(inspect(rec, { depth: 10 }).includes("SECRET-HMAC-KEY-VALUE"), false);
  assert.equal(JSON.stringify(rec).includes("SECRET-HMAC-KEY-VALUE"), false);
});

// --- Hashing and timestamps ------------------------------------------------

test("payloads JSON cannot represent hash without throwing, and distinctly", () => {
  const circular: Record<string, unknown> = {};
  circular["self"] = circular;
  const hashes = [new Map([["a", 1]]), new Set([1]), {}, Buffer.from("hi"), circular, NaN, () => 1, new Error("x")].map(hashPayload);
  assert.equal(new Set(hashes).size, hashes.length);
  assert.equal(hashPayload({ a: [1, "x"] }), hashPayload(JSON.parse('{"a": [1, "x"]}')), "plain JSON hashes as before");
});

test("only a granted timestamp over this head and nonce counts as one", async () => {
  const head = "ab".repeat(32);
  const nonce = Buffer.from("0102030405060708", "hex");
  assert.match(checkResponse(Buffer.from("<html>login</html>"), Buffer.from(head, "hex"), nonce)!, /not a timestamp response/);
  // A well-formed rejection: TimeStampResp { status { 2 } }.
  assert.match(checkResponse(Buffer.from("30053003020102", "hex"), Buffer.from(head, "hex"), nonce)!, /refused \(status 2\)/);
  // Granted, but the token is not over this head.
  const query = makeQuery("cd".repeat(32), nonce);
  const fake = Buffer.concat([Buffer.from([0x30, 0x80 + 1]), Buffer.from([5 + 13 + query.length]),
    Buffer.from("3003020100", "hex"), Buffer.from("060b2a864886f70d0109100104", "hex"), query]);
  assert.match(checkResponse(fake, Buffer.from(head, "hex"), nonce)!, /not over this chain head/);

  // And a server answering 200 with a page of its own is a gap, not an anchor.
  const server = http.createServer((_req, res) => { res.writeHead(200, { "content-type": "text/html" }); res.end("<html>captive portal</html>"); });
  await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
  const port = (server.address() as { port: number }).port;
  try {
    const result = await timestampHead(head, [`http://127.0.0.1:${port}/`], 5000);
    assert.equal(result.ok, false);
    assert.match(result.error!, /not a timestamp response/);
  } finally {
    server.close();
  }
});
