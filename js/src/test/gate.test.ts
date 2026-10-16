import assert from "node:assert/strict";
import * as fs from "node:fs";
import { test } from "node:test";

import { verifyChain } from "../chain.js";
import { Covenant } from "../covenant.js";
import { Gate } from "../gate.js";
import { verifyReceipt } from "../receipt.js";
import { tmpdir } from "./helpers.js";

const covenant = Covenant.fromYamlString(`
agent: loan-processor
rules:
  - permit: read_credit_score
  - require_approval: approve_loan
    when: "amount > 50000"
  - permit: approve_loan
    when: "amount <= 50000"
  - forbid: delete_records
`);

test("authorize, seal, verify; receipts and chain on disk", () => {
  const dir = tmpdir();
  const gate = new Gate({ covenant, runsDir: dir, hmacKey: "k" });
  assert.equal(gate.signingMethod, "ed25519", "the chain key must not downgrade receipt signatures");
  const r = gate.authorize({ agentId: "loan-processor", actionName: "approve_loan", payload: { applicant: "x", amount: 1000 }, context: { amount: 1000 } });
  assert.equal(r.authorized, true);
  assert.equal(r.decision, "permit");
  assert.equal(r.status, "authorized");
  assert.equal(r.covenant_hash, covenant.hash);
  assert.equal(r.chain_hash.length, 64);
  gate.seal(r, { result: { approved: true }, status: "success" });
  assert.equal(r.status, "sealed");
  const v = gate.verify(r);
  assert.equal(v.overall, true);
  assert.equal(v.seal_valid, true);
  assert.equal(verifyReceipt(r.toDict(), gate.publicKeyHex).verified, true);

  const denied = gate.authorize({ agentId: "loan-processor", actionName: "delete_records" });
  assert.equal(denied.authorized, false);
  assert.equal(denied.status, "denied");
  assert.equal(gate.verify(denied).overall, true, "a signed denial verifies; read authorized for permission");

  const pending = gate.authorize({ agentId: "loan-processor", actionName: "approve_loan", context: { amount: 75000 } });
  assert.equal(pending.decision, "require_approval");
  assert.equal(pending.authorized, false, "no approver registered means deny");

  const files = fs.readdirSync(dir);
  assert.equal(files.filter((f) => f.endsWith(".receipt.json")).length, 3);
  // authorize x3 + seal x1 = 4 chained records
  const chain = verifyChain(dir, "k");
  assert.equal(chain.intact, true);
  assert.equal(chain.verified_records, 4);
});

test("approval callback, sync and async", async () => {
  const dir = tmpdir();
  const sync = new Gate({ covenant, runsDir: dir, hmacKey: "k", onApprovalNeeded: () => true });
  const ok = sync.authorize({ agentId: "a", actionName: "approve_loan", context: { amount: 75000 } });
  assert.equal(ok.authorized, true);
  assert.equal(ok.decision, "require_approval");

  const asyncGate = new Gate({ covenant, runsDir: tmpdir(), hmacKey: "k", onApprovalNeeded: async () => false });
  assert.throws(() => asyncGate.authorize({ agentId: "a", actionName: "approve_loan", context: { amount: 75000 } }), TypeError);
  const r = await asyncGate.authorizeAsync({ agentId: "a", actionName: "approve_loan", context: { amount: 75000 } });
  assert.equal(r.authorized, false);
  assert.equal(r.status, "denied");
});

test("delegation chain walks back to the root", () => {
  const gate = new Gate({ covenant, runsDir: tmpdir(), hmacKey: "k" });
  const root = gate.authorize({ agentId: "a", actionName: "read_credit_score" });
  const child = gate.authorize({ agentId: "b", actionName: "read_credit_score", parentReceipt: root });
  const chain = gate.walkDelegationChain(child);
  assert.deepEqual(chain.map((r) => r.receipt_id), [root.receipt_id, child.receipt_id]);
  assert.equal(gate.verify(child).has_parent, true);
});
