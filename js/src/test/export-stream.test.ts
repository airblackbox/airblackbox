// The export streams from the runs directory (streamEvidenceBundleV1). It
// must write what the in-memory export (generateEvidenceBundleV1 over
// loadRecords) writes, member for member, for any directory, while holding
// an index entry per record rather than the records.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";

import { unzipSync } from "fflate";

import { computeHead, headOverEntries } from "../anchor.js";
import { generateEvidenceBundleV1, streamEvidenceBundleV1, type AnchorManifest } from "../bundle.js";
import { pythonJson } from "../canonical.js";
import { AuditChain, indexRecords, loadRecords, loadRecordsReport, verifyChain, verifyRecords } from "../chain.js";
import { ReceiptSigner } from "../receipt.js";
import { record } from "../recorder.js";
import { hasAirSdk, python, tmpdir } from "./helpers.js";

const KEY = "export-key";
const ANCHOR: AnchorManifest = { anchored: false, reason: "anchoring disabled" };
const SYSTEM = { name: "agent", high_risk_rationale: "", deployer: "" };

/** The export as it was before streaming: every record in memory. */
function inMemory(dir: string, signer: ReceiptSigner, out: string, extra: string[] = []): string {
  const { records, unreadable } = loadRecordsReport(dir);
  const verification = verifyRecords(records, KEY);
  const chained = records.filter((r) => r.chain_hash);
  const problems = [...(unreadable.length ? [`${unreadable.length} record file(s) could not be read: ${unreadable.slice(0, 3).join(", ")}`] : []), ...extra];
  const fullyIntact = verification.intact && verification.verified_records === records.length && problems.length === 0;
  return generateEvidenceBundleV1({
    chainEntries: chained, tenant: "agent", signer, system: SYSTEM, anchor: ANCHOR, outputDir: out,
    chainVerification: {
      fully_intact: fullyIntact,
      ...verification,
      ...(problems.length ? { intact: false, first_break_at: verification.first_break_at ?? chained.length, problems } : {}),
    },
  }).path;
}

async function streamed(dir: string, signer: ReceiptSigner, out: string, extra: string[] = [], yieldEvery?: number): Promise<string> {
  const { entries, unreadable } = indexRecords(dir);
  const r = await streamEvidenceBundleV1({ runsDir: dir, entries, unreadable, signingKey: KEY, tenant: "agent", signer,
    system: SYSTEM, anchor: ANCHOR, outputDir: out, problems: extra, yieldEvery });
  return r.path;
}

function members(bundle: string): Record<string, string> {
  const z = unzipSync(fs.readFileSync(bundle));
  return Object.fromEntries(Object.entries(z).map(([k, v]) => [k, Buffer.from(v).toString("utf8")]));
}

function assertSameBundle(a: string, b: string, label: string): void {
  const ma = members(a);
  const mb = members(b);
  assert.deepEqual(Object.keys(mb).sort(), Object.keys(ma).sort(), label);
  for (const name of Object.keys(ma)) {
    if (name === "manifest.json") continue;
    assert.equal(mb[name], ma[name], `${label}: ${name}`);
  }
  const fa = JSON.parse(ma["manifest.json"]!) as Record<string, any>;
  const fb = JSON.parse(mb["manifest.json"]!) as Record<string, any>;
  for (const k of ["counts", "system", "files", "anchor", "tenant", "frameworks"]) assert.deepEqual(fb[k], fa[k], `${label}: manifest ${k}`);
}

/** The directory's own signing identity, which signed its receipts. */
function dirSigner(dir: string): ReceiptSigner {
  const { seed } = JSON.parse(fs.readFileSync(path.join(dir, ".air-receipt-key"), "utf8")) as { seed: string };
  return new ReceiptSigner({ privateKey: Buffer.from(seed, "hex") });
}

/** A directory with the shapes a real one collects. */
function varied(dir: string): void {
  if (hasAirSdk()) {
    python(`
import os
os.environ["TRUST_SIGNING_KEY"] = ${JSON.stringify(KEY)}
import air_blackbox as air
rec = air.record("agent", runs_dir=${JSON.stringify(dir)}, anchor=False)
rec.action("python_step", "from the Python SDK", human_reviewer="dana@acme.example")
rec.action("reject_candidate", "fictional candidate 4", decision_type="reject")
`);
  }
  const rec = record("agent", { runsDir: dir, anchor: false, hmacKey: KEY });
  rec.action("read_ticket", "ticket #4821 résumé \u{1F600} \"quoted\" \\ back\nslash");
  rec.action("reject_candidate", "fictional candidate 17", { humanReviewer: "dana@acme.example", decisionType: "reject", context: { score: 2.5, rank: 3, ratio: 1.0, big: 1e21, tiny: 5e-7 } });
  rec.action("score_candidate", "fictional candidate 18", { decisionType: "rank" });
  rec.action("delete_records", "all", { status: "blocked" });
  rec.observe("llm_call", { model: "fictional-model", tokens: { prompt: 12, completion: 7 }, nested: [{ a: [1, 2.0, "x"] }] });
  rec.action("human_approval", "", { context: { approver: "lee@example.com" } });
  rec.close();
}

test("a streamed export writes what the in-memory export writes, member for member", async () => {
  const dir = tmpdir();
  varied(dir);
  const signer = dirSigner(dir);
  const out = tmpdir();
  const bundle = await streamed(dir, signer, out);
  assertSameBundle(inMemory(dir, signer, out), bundle, "intact");
  const chainDoc = JSON.parse(members(bundle)["verification/chain.json"]!) as Record<string, any>;
  assert.equal(chainDoc["verification_at_export"]["fully_intact"], true, "the Python and TypeScript records form one intact chain");
  // A pause every record changes nothing but when other work runs.
  assertSameBundle(inMemory(dir, signer, out), await streamed(dir, signer, out, [], 1), "yieldEvery 1");
  assert.deepEqual(fs.readdirSync(out).filter((f) => !f.endsWith(".air-evidence")), [], "no work files left behind");
});

test("streamed and in-memory exports agree on a broken, holed or partly unchained directory", async () => {
  const cases: Array<[string, (dir: string) => string[]]> = [
    ["an edited record", (dir) => {
      const rec = loadRecords(dir)[2]!;
      const file = path.join(dir, `${rec.run_id}.air.json`);
      fs.writeFileSync(file, fs.readFileSync(file, "utf8").replace("fictional candidate 18", "fictional candidate 81"));
      return [];
    }],
    ["a torn record", (dir) => {
      fs.writeFileSync(path.join(dir, `${loadRecords(dir)[1]!.run_id}.air.json`), "{ torn");
      return [];
    }],
    ["a record outside the chain, and the recorder's own missing-head problem", (dir) => {
      fs.writeFileSync(path.join(dir, "outside.air.json"), JSON.stringify({ run_id: "outside", timestamp: "2026-01-01T00:00:00Z", type: "note" }));
      return ["the newest record this process wrote is missing from the directory"];
    }],
    ["records written compactly, as other writers may", (dir) => {
      for (const r of loadRecords(dir).slice(0, 3)) fs.writeFileSync(path.join(dir, `${r.run_id}.air.json`), pythonJson(r));
      return [];
    }],
  ];
  for (const [label, damage] of cases) {
    const dir = tmpdir();
    varied(dir);
    const signer = dirSigner(dir);
    const extra = damage(dir);
    const out = tmpdir();
    assertSameBundle(inMemory(dir, signer, out, extra), await streamed(dir, signer, out, extra), label);
  }
});

test("the index orders a directory exactly as loadRecords does, odd files included", () => {
  const dir = tmpdir();
  varied(dir);
  const chain = new AuditChain(dir, KEY, true);
  for (let i = 0; i < 3; i++) chain.write({ type: "same_second", timestamp: "2026-01-01T00:00:00Z" });
  // Hand-edited files the fast path must not misread: a chain_seq that is a
  // string or a fraction, a key given twice (a parser keeps the last), a
  // record cut short, a top-level value that is an object.
  const odd = (name: string, text: string): void => fs.writeFileSync(path.join(dir, `${name}.air.json`), text);
  odd("seq-string", `{\n  "chain_hash": "aa",\n  "chain_seq": "2",\n  "run_id": "seq-string",\n  "timestamp": "2026-01-01T00:00:01Z"\n}\n`);
  odd("seq-fraction", `{\n  "chain_hash": "bb",\n  "chain_seq": 2.5,\n  "run_id": "seq-fraction",\n  "timestamp": "2026-01-01T00:00:01Z"\n}\n`);
  odd("seq-twice", `{\n  "chain_hash": "cc",\n  "chain_seq": 1,\n  "chain_seq": 99,\n  "run_id": "seq-twice",\n  "timestamp": "2026-01-01T00:00:01Z"\n}\n`);
  odd("hash-twice", `{\n  "chain_hash": "dd",\n  "chain_hash": "",\n  "chain_seq": 3,\n  "run_id": "hash-twice"\n}\n`);
  odd("cut-short", `{\n  "chain_hash": "ee",\n  "chain_seq": 4,\n  "run_id": "cut-sh`);
  odd("ts-object", `{\n  "chain_hash": "ff",\n  "chain_seq": 5,\n  "run_id": "ts-object",\n  "timestamp": {\n    "at": 1\n  }\n}\n`);
  const fromIndex = indexRecords(dir);
  const { records, unreadable } = loadRecordsReport(dir);
  const ids = (rs: Array<{ run_id?: unknown; chain_hash?: unknown }>) => rs.map((r) => `${String(r.run_id)}:${String(r.chain_hash ?? "")}`);
  assert.deepEqual(ids(fromIndex.entries.map((e) => ({ run_id: e.runId, chain_hash: e.chainHash }))), ids(records));
  assert.deepEqual(fromIndex.unreadable, unreadable);
  // The anchored head too, as computed from the records themselves.
  assert.equal(computeHead(dir), headOverEntries(records.filter((r) => r.chain_hash).map((r) => [Number(r.chain_seq ?? 0), String(r.chain_hash)])));
});

test("resuming from the stored head continues the chain exactly as re-hashing it would", () => {
  const dir = tmpdir();
  varied(dir);
  const a = new AuditChain(dir, KEY, true);
  a.write({ type: "after_resume" });
  const v = verifyChain(dir, KEY);
  assert.equal(v.intact, true);
  assert.equal(v.verified_records, loadRecords(dir).length);
});

test("an export lets other work run while it writes", async () => {
  const dir = tmpdir();
  const chain = new AuditChain(dir, KEY, true);
  for (let i = 0; i < 3000; i++) chain.write({ type: "step", detail: `fictional step ${i}` });
  let ticks = 0;
  const timer = setInterval(() => ticks++, 1);
  try {
    await streamed(dir, new ReceiptSigner(), tmpdir());
  } finally {
    clearInterval(timer);
  }
  assert.ok(ticks > 0, "a timer fired while the export was running");
});

test("files the agent opens while an export runs stay open", async () => {
  const dir = tmpdir();
  const chain = new AuditChain(dir, KEY, true);
  for (let i = 0; i < 40; i++) chain.write({ type: "step", receipt: { receipt_id: `r-${i}` } });
  const mine = path.join(tmpdir(), "agent-file");
  fs.writeFileSync(mine, "the agent's own data");
  const opened: number[] = [];
  let done = false;
  const agent = (): void => {
    if (done) return;
    opened.push(fs.openSync(mine, "r"));
    setImmediate(agent);
  };
  setImmediate(agent);
  try {
    await streamed(dir, new ReceiptSigner(), tmpdir(), [], 1);
  } finally {
    done = true;
  }
  try {
    for (const fd of opened) assert.equal(fs.readFileSync(fd, "utf8"), "the agent's own data");
  } finally {
    for (const fd of opened) fs.closeSync(fd);
  }
});

test("differential: the Python SDK verifies a streamed export and pins its signer", { skip: !hasAirSdk() && "air_blackbox SDK not importable" }, async () => {
  const dir = tmpdir();
  varied(dir);
  const signer = dirSigner(dir);
  const bundle = await streamed(dir, signer, tmpdir());
  const fingerprint = `ed25519:${createHash("sha256").update(Buffer.from(signer.publicKeyHex!, "hex")).digest("hex").slice(0, 16)}`;
  const out = python(`
import io, json
from air_blackbox.evidence_verify import verify_bundle
buf = io.StringIO()
r = verify_bundle(${JSON.stringify(bundle)}, hmac_key=${JSON.stringify(KEY)}, expect_key=${JSON.stringify(fingerprint)}, out=buf)
print(json.dumps({"records": r["records"], "alterations": r["alterations"], "log": buf.getvalue()}))`);
  const res = JSON.parse(out) as Record<string, any>;
  assert.equal(res["records"], loadRecords(dir).length, res["log"]);
  assert.equal(res["alterations"], 0, res["log"]);
  assert.match(res["log"], /signer pinned and matched/);
});

// Opt-in: AIR_SCALE_TEST=N (or 1 for 100,000) writes N records and exports
// them in a child process whose heap is capped well below what holding the
// records would take. CI runs 20,000, where the in-memory export runs out of
// heap under the same cap.
const SCALE = process.env["AIR_SCALE_TEST"] === "1" ? 100_000 : Number(process.env["AIR_SCALE_TEST"] ?? 0);

test(`scale: ${SCALE || "N"} records export under a 160 MB heap`, { skip: !SCALE && "set AIR_SCALE_TEST to run", timeout: 30 * 60_000 }, () => {
  const dir = tmpdir();
  const chain = new AuditChain(dir, KEY, true);
  for (let i = 0; i < SCALE; i++) {
    chain.write({ type: "agent_action", action: i % 50 ? "step" : "reject_candidate", detail: `fictional order A-${i}`,
      context: { order: `A-${i}`, amount: i % 1000, note: "x".repeat(200) } });
  }
  const recorder = new URL("../recorder.js", import.meta.url).href;
  const out = tmpdir();
  const child = spawnSync(process.execPath, ["--max-old-space-size=160", "--input-type=module", "-e", `
import { Recorder } from ${JSON.stringify(recorder)};
const rec = new Recorder("scale", { runsDir: ${JSON.stringify(dir)}, anchor: false, hmacKey: ${JSON.stringify(KEY)} });
const bundle = await rec.export(${JSON.stringify(out)});
console.log(JSON.stringify({ bundle, note: rec.lastExportNote }));`], { encoding: "utf8", maxBuffer: 1 << 20 });
  assert.equal(child.status, 0, child.stderr);
  const { bundle, note } = JSON.parse(child.stdout.trim().split("\n").at(-1)!) as { bundle: string; note: string };
  assert.equal(note, "");
  const chainDoc = JSON.parse(Buffer.from(unzipSync(fs.readFileSync(bundle), { filter: (f) => f.name === "verification/chain.json" })["verification/chain.json"]!).toString("utf8")) as Record<string, any>;
  assert.equal(chainDoc["verification_at_export"]["fully_intact"], true);
  assert.equal(chainDoc["records"].length, SCALE);
});
