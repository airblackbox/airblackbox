import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";

import { unzipSync } from "fflate";

import { Covenant } from "../covenant.js";
import { record } from "../recorder.js";
import { verifyReceipt } from "../receipt.js";
import { hasAirSdk, python, tmpdir } from "./helpers.js";

function members(bundle: string): Record<string, string> {
  const z = unzipSync(fs.readFileSync(bundle));
  return Object.fromEntries(Object.entries(z).map(([k, v]) => [k, Buffer.from(v).toString("utf8")]));
}

test("record -> export produces a v1 bundle with consistent manifest", async () => {
  const dir = tmpdir();
  const rec = record("support-agent", { runsDir: dir, anchor: false });
  rec.action("read_ticket", "ticket #4821");
  const refund = rec.action("issue_refund", "order 991, $40", { humanReviewer: "dana@acme.example", decisionType: "refund" });
  assert.equal(refund.allowed, true);
  assert.equal(rec.recordCount, 2);
  const bundle = await rec.export();
  assert.ok(bundle.endsWith(".air-evidence"));
  assert.ok(fs.existsSync(bundle));

  const m = members(bundle);
  for (const name of ["manifest.json", "records/actions.jsonl", "verification/chain.json", "verification/receipts.json", "verification/public_key.pem", "mapping/sb26-189.json"]) {
    assert.ok(name in m, `missing ${name}`);
  }
  const manifest = JSON.parse(m["manifest.json"]!) as Record<string, any>;
  assert.equal(manifest["tenant"], "support-agent");
  assert.equal(manifest["counts"]["actions"], 2);
  assert.equal(manifest["counts"]["screening_decisions"], 1);
  assert.equal(manifest["counts"]["screening_decisions_missing_reviewer"], 0);
  assert.equal(manifest["signature"]["alg"], "ed25519");
  assert.equal(manifest["anchor"]["anchored"], false);
  assert.match(manifest["retention_until"], /^\d{4}-\d{2}-\d{2}$/);
  const lines = m["records/actions.jsonl"]!.trim().split("\n");
  assert.equal(lines.length, 2);
  for (const line of lines) {
    const r = JSON.parse(line) as Record<string, any>;
    assert.equal(verifyReceipt(r["receipt"], rec.publicKeyHex).verified, true);
  }
  assert.ok(fs.existsSync(path.join(dir, ".air-receipt-key")));
});

test("a covenant decides each action; default-deny for unknown names", () => {
  const cov = Covenant.fromYamlString("agent: a\nrules:\n  - permit: read_ticket\n  - require_approval: issue_refund\n    when: \"amount > 100\"\n  - permit: issue_refund\n    when: \"amount <= 100\"\n");
  const rec = record("a", { runsDir: tmpdir(), covenant: cov, anchor: false });
  assert.equal(rec.action("read_ticket").decision, "permit");
  assert.equal(rec.action("issue_refund", "", { context: { amount: 40 } }).allowed, true);
  const big = rec.action("issue_refund", "", { context: { amount: 400 } });
  assert.equal(big.decision, "require_approval");
  assert.equal(big.allowed, false);
  const bad = rec.action("delete_everything");
  assert.equal(bad.decision, "forbid");
  const v = rec.verify();
  assert.equal(v.intact, true);
  assert.equal(v.verified_records, 4);
  // guard values are not stored; context values are
  const files = fs.readdirSync(rec.runsDir).filter((f) => f.endsWith(".air.json"));
  const docs = files.map((f) => JSON.parse(fs.readFileSync(path.join(rec.runsDir, f), "utf8")) as Record<string, any>);
  const blocked = docs.find((d) => d["action"] === "delete_everything")!;
  assert.equal(blocked["status"], "blocked");
  assert.equal(blocked["covenant_hash"], cov.hash);
  const guarded = rec.action("issue_refund", "", { guard: { amount: 40 } });
  assert.equal(guarded.allowed, true);
  const last = JSON.parse(fs.readFileSync(path.join(rec.runsDir, fs.readdirSync(rec.runsDir).filter((f) => f.endsWith(".air.json")).find((f) => {
    const d = JSON.parse(fs.readFileSync(path.join(rec.runsDir, f), "utf8")) as { chain_hash: string };
    return d.chain_hash === guarded.chain_hash;
  })!), "utf8")) as Record<string, unknown>;
  assert.equal(last["context"], undefined);
});

test("a second recorder on the same directory keeps the identity and continues the chain", async () => {
  const dir = tmpdir();
  const first = record("a", { runsDir: dir, anchor: false });
  first.action("step_one");
  const b1 = await first.export();
  const second = record("a", { runsDir: dir, anchor: false });
  second.action("step_two");
  const b2 = await second.export();
  assert.equal(first.publicKeyHex, second.publicKeyHex);
  const m2 = JSON.parse(members(b2)["manifest.json"]!) as { counts: { actions: number } };
  assert.equal(m2.counts.actions, 2);
  assert.equal(JSON.parse(members(b1)["manifest.json"]!).counts.actions, 1);
  assert.equal(second.verify().verified_records, 2);
});

test("an unreadable key file is refused, never overwritten", () => {
  const dir = tmpdir();
  fs.writeFileSync(path.join(dir, ".air-receipt-key"), "not json");
  assert.throws(() => record("a", { runsDir: dir, anchor: false }), /not an Ed25519 key/);
  assert.equal(fs.readFileSync(path.join(dir, ".air-receipt-key"), "utf8"), "not json");
});

test("await using exports on scope exit", async () => {
  const dir = tmpdir();
  let saved: string | undefined;
  {
    await using rec = record("a", { runsDir: dir, anchor: false });
    rec.action("x");
    saved = undefined;
    assert.equal(rec.bundlePath, undefined);
    // capture after dispose via directory listing below
  }
  saved = fs.readdirSync(dir).find((f) => f.endsWith(".air-evidence"));
  assert.ok(saved, "bundle written on dispose");
});

test("differential: the Python SDK verifies our bundle end to end", { skip: !hasAirSdk() && "air_blackbox SDK not importable" }, async () => {
  const dir = tmpdir();
  const rec = record("ts-agent", { runsDir: dir, anchor: false, hmacKey: "chain-key" });
  rec.action("read_ticket", "ticket #4821 résumé \u{1F600}");
  rec.action("reject_candidate", "candidate 17", { humanReviewer: "dana@acme.example", decisionType: "reject", context: { score: 2.5, rank: 3 } });
  rec.action("score_candidate", "candidate 18", { decisionType: "rank" });
  const bundle = await rec.export();
  const out = python(`
import io, json
from air_blackbox.evidence_verify import verify_bundle
buf = io.StringIO()
r = verify_bundle(${JSON.stringify(bundle)}, hmac_key="chain-key", expect_key=${JSON.stringify(rec.fingerprint)}, out=buf)
print(json.dumps({"records": r["records"], "alterations": r["alterations"], "receipts_checked": r["receipts_checked"], "fingerprint": r["fingerprint"], "log": buf.getvalue()}))`);
  const res = JSON.parse(out) as Record<string, any>;
  assert.equal(res["records"], 3, res["log"]);
  assert.equal(res["alterations"], 0, res["log"]);
  assert.equal(res["receipts_checked"], 3, res["log"]);
  assert.equal(res["fingerprint"], rec.fingerprint);
  assert.match(res["log"], /signer pinned and matched/);
  assert.match(res["log"], /\[3\/6\] Chain: full HMAC recompute over 3 records: OK/);
  assert.match(res["log"], /\[5\/6\] Counts: manifest matches records/);

  // Tamper with a record inside the bundle: the SDK must reject it.
  const z = unzipSync(fs.readFileSync(bundle));
  const jsonl = Buffer.from(z["records/actions.jsonl"]!).toString("utf8").replace("candidate 17", "candidate 99");
  const { zipSync } = await import("fflate");
  z["records/actions.jsonl"] = new Uint8Array(Buffer.from(jsonl));
  const tampered = bundle + ".tampered";
  fs.writeFileSync(tampered, zipSync(z));
  const bad = python(`
import io
from air_blackbox.evidence_verify import verify_bundle, VerificationFailure
try:
    verify_bundle(${JSON.stringify(tampered)}, hmac_key="chain-key", out=io.StringIO()); print("PASSED")
except VerificationFailure as e:
    print("FAILED", e)`).trim();
  assert.match(bad, /^FAILED/);
});

test("differential: the Python SDK's record() and ours share one chain and one identity", { skip: !hasAirSdk() && "air_blackbox SDK not importable" }, async () => {
  const dir = tmpdir();
  python(`
import air_blackbox as air
rec = air.record("shared", runs_dir=${JSON.stringify(dir)}, anchor=False)
rec.action("python_step", "from the Python SDK", human_reviewer="dana@acme.example")
`);
  const rec = record("shared", { runsDir: dir, anchor: false });
  rec.action("node_step", "from the Node SDK");
  const v = rec.verify();
  assert.equal(v.intact, true);
  assert.equal(v.verified_records, 2);
  const bundle = await rec.export();
  const out = python(`
import io, json
from air_blackbox.evidence_verify import verify_bundle
r = verify_bundle(${JSON.stringify(bundle)}, out=io.StringIO())
print(json.dumps([r["records"], r["alterations"], r["receipts_checked"], r["fingerprint"]]))`);
  const [records, alterations, receipts, fp] = JSON.parse(out) as [number, number, number, string];
  assert.equal(records, 2);
  assert.equal(alterations, 0);
  assert.equal(receipts, 2);
  assert.equal(fp, `ed25519:${python(`import hashlib; print(hashlib.sha256(bytes.fromhex(${JSON.stringify(rec.publicKeyHex)})).hexdigest()[:16])`).trim()}`);
});
