import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";

import { AuditChain, loadRecords, verifyChain, verifyRecords } from "../chain.js";
import { hasAirSdk, hasPython, python, tmpdir } from "./helpers.js";

const KEY = "test-secret-key-32-bytes-minimum!";

const PY_VERIFY = `
import glob, hashlib, hmac, json, os, sys
runs, key = sys.argv[1], sys.argv[2].encode()
recs = []
for p in glob.glob(os.path.join(runs, "*.air.json")):
    recs.append(json.load(open(p)))
recs.sort(key=lambda r: (r.get("chain_seq") or 0, r.get("timestamp") or ""))
prev = b"genesis"
for i, r in enumerate(recs):
    if not r.get("chain_hash"): continue
    body = {k: v for k, v in r.items() if k != "chain_hash"}
    h = hmac.new(key, prev + json.dumps(body, sort_keys=True).encode(), hashlib.sha256)
    if h.hexdigest() != r["chain_hash"]:
        print("BREAK", i); sys.exit(0)
    prev = h.digest()
print("OK", len(recs))
`;

function pyVerify(runs: string, key = KEY): string {
  return python(PY_VERIFY.replace("sys.argv[1], sys.argv[2]", `${JSON.stringify(runs)}, ${JSON.stringify(key)}`)).trim();
}

test("writes chained records the verifier accepts, and detects tampering", () => {
  const dir = tmpdir();
  const chain = new AuditChain(dir, KEY);
  const h1 = chain.write({ type: "agent_action", action: "read_ticket", detail: "ticket #4821", n: 1.5, u: "café \u{1F600}" });
  chain.write({ type: "agent_action", action: "issue_refund", context: { amount: 40, order: "991" } });
  chain.write({ type: "llm_call", model: "gpt-4o", tokens: { prompt: 10, completion: 5, total: 15 } });
  assert.equal(chain.recordCount, 3);
  assert.equal(chain.currentHash.length, 64);
  assert.equal(h1.length, 64);

  const records = loadRecords(dir);
  assert.deepEqual(records.map((r) => Number(r.chain_seq)), [1, 2, 3]);
  const ok = verifyRecords(records, KEY);
  assert.equal(ok.intact, true);
  assert.equal(ok.verified_records, 3);

  // Tamper with the second record on disk: the break is reported there.
  const second = records[1]!;
  const file = path.join(dir, `${second.run_id}.air.json`);
  const doc = JSON.parse(fs.readFileSync(file, "utf8")) as Record<string, unknown>;
  (doc["context"] as Record<string, unknown>)["amount"] = 4000;
  fs.writeFileSync(file, JSON.stringify(doc, null, 2));
  const bad = verifyChain(dir, KEY);
  assert.equal(bad.intact, false);
  assert.equal(bad.first_break_at, 1);
  assert.equal(bad.first_break_run_id, second.run_id);
});

test("a wrong key fails verification", () => {
  const dir = tmpdir();
  new AuditChain(dir, KEY).write({ type: "x" });
  assert.equal(verifyChain(dir, "other-key").intact, false);
  assert.equal(verifyChain(dir, KEY).intact, true);
});

test("resume continues an existing chain instead of starting a second genesis", () => {
  const dir = tmpdir();
  const a = new AuditChain(dir, KEY);
  a.write({ type: "x", step: 1 });
  a.write({ type: "x", step: 2 });
  const b = new AuditChain(dir, KEY, true);
  assert.equal(b.nextSeq, 3);
  b.write({ type: "x", step: 3 });
  const v = verifyChain(dir, KEY);
  assert.equal(v.intact, true);
  assert.equal(v.verified_records, 3);
  // Without resume the third record would be a new genesis and the chain breaks.
  const dir2 = tmpdir();
  new AuditChain(dir2, KEY).write({ type: "x" });
  new AuditChain(dir2, KEY).write({ type: "x" });
  assert.equal(verifyChain(dir2, KEY).intact, false);
});

test("the key is resolved like the Python SDK: env, then .air-signing-key, then default", () => {
  const dir = tmpdir();
  fs.writeFileSync(path.join(dir, ".air-signing-key"), "from-file\n");
  new AuditChain(dir).write({ type: "x" });
  assert.equal(verifyChain(dir, "from-file").intact, true);
  assert.equal(verifyChain(dir).intact, true);
  assert.equal(verifyChain(dir, "air-blackbox-default").intact, false);
});

test("differential: Python recomputes every chain hash we wrote", { skip: !hasPython() && "python3 not available" }, () => {
  const dir = tmpdir();
  const chain = new AuditChain(dir, KEY);
  for (let i = 0; i < 25; i++) {
    chain.write({
      type: i % 2 ? "tool_call" : "llm_call",
      i,
      f: i / 7,
      big: 2 ** 60 + i,
      tiny: 1e-9 * i,
      s: "résumé \u{1F600} \"q\" \\ \n",
      nested: { list: [1, 2.5, null, true, { k: "v" }], empty: {}, none: null },
    });
  }
  assert.equal(pyVerify(dir), "OK 25");
});

test("differential: the Python SDK's verifier reads our records; we read the SDK's", { skip: !hasAirSdk() && "air_blackbox SDK not importable" }, () => {
  // Ours -> theirs.
  const dir = tmpdir();
  const chain = new AuditChain(dir, KEY);
  chain.write({ type: "agent_action", action: "a", context: { amount: 12.5 } });
  chain.write({ type: "agent_action", action: "b" });
  const theirs = python(`
import json
from air_blackbox.replay.engine import ReplayEngine
e = ReplayEngine(runs_dir=${JSON.stringify(dir)}); n = e.load(); v = e.verify_chain(${JSON.stringify(KEY)})
print(json.dumps({"n": n, "intact": v.intact, "verified": v.verified_records}))`);
  assert.deepEqual(JSON.parse(theirs), { n: 2, intact: true, verified: 2 });

  // Theirs -> ours, including a float the SDK writes as 2.0.
  const dir2 = tmpdir();
  python(`
from air_blackbox.trust.chain import AuditChain
c = AuditChain(runs_dir=${JSON.stringify(dir2)}, signing_key=${JSON.stringify(KEY)})
c.write({"type": "agent_action", "action": "x", "score": 2.0, "ratio": 0.1, "n": 10**20, "u": "caf\\u00e9"})
c.write({"type": "agent_action", "action": "y", "list": [1.0, 2, 3.5]})`);
  const v = verifyChain(dir2, KEY);
  assert.equal(v.intact, true);
  assert.equal(v.verified_records, 2);

  // And we can append to the SDK's chain, and the SDK still verifies it.
  new AuditChain(dir2, KEY, true).write({ type: "agent_action", action: "z" });
  const again = python(`
from air_blackbox.replay.engine import ReplayEngine
e = ReplayEngine(runs_dir=${JSON.stringify(dir2)}); e.load(); v = e.verify_chain(${JSON.stringify(KEY)})
print(v.intact, v.verified_records)`).trim();
  assert.equal(again, "True 3");
});
