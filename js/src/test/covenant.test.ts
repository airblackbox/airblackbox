import assert from "node:assert/strict";
import { test } from "node:test";

import { Covenant, Rule, evalCondition } from "../covenant.js";
import { hasAirSdk, python } from "./helpers.js";

const YAML = `
agent: loan-processor
version: "1.0"
description: Loan processing agent policy
rules:
  - permit: read_credit_score
  - permit: calculate_risk
  - require_approval: approve_loan
    when: "amount > 50000"
  - permit: approve_loan
    when: "amount <= 50000"
  - forbid: delete_records
  - forbid: send_email
    unless: human_approved
  - permit: readonly_tools
    category: readonly
`;

test("evaluate: precedence, guards and default deny", () => {
  const c = Covenant.fromYamlString(YAML);
  assert.equal(c.agent, "loan-processor");
  assert.equal(c.rules.length, 7);
  assert.equal(c.evaluate("read_credit_score"), "permit");
  assert.equal(c.evaluate("unknown_action"), "forbid");
  assert.equal(c.evaluate("approve_loan", { amount: 75000 }), "require_approval");
  assert.equal(c.evaluate("approve_loan", { amount: 1000 }), "permit");
  assert.equal(c.evaluate("approve_loan", { amount: "1,000,000" }), "forbid", "indeterminate guard never grants");
  assert.equal(c.evaluate("approve_loan"), "forbid", "missing field never grants");
  assert.equal(c.evaluate("delete_records"), "forbid");
  assert.equal(c.evaluate("send_email"), "forbid");
  assert.equal(c.evaluate("send_email", { human_approved: true }), "forbid", "unless only lifts the forbid; nothing permits");
  assert.equal(c.evaluate("list_files", { category: "readonly" }), "permit");
  assert.equal(c.evaluate("delete_records", { category: "readonly" }), "forbid", "forbid wins over a category permit");
});

test("a '*' target matches every action, as in the Python SDK", () => {
  const c = Covenant.fromYamlString('agent: a\nrules:\n  - permit: "*"\n    category: readonly\n  - forbid: delete_records\n');
  assert.equal(c.evaluate("anything_at_all"), "permit", "category does not narrow a wildcard target");
  assert.equal(c.evaluate("delete_records"), "forbid");
});

test("a forbid with a garbled guard stays active", () => {
  const c = new Covenant({ agent: "a", rules: [new Rule({ action: "forbid", target: "x", when: "nonsense" }), new Rule({ action: "permit", target: "x" })] });
  assert.equal(c.evaluate("x"), "forbid");
});

test("evalCondition mirrors the Python tri-state", () => {
  assert.equal(evalCondition("amount > 50000", { amount: 75000 }), true);
  assert.equal(evalCondition("amount > 50000", { amount: "75000" }), true);
  assert.equal(evalCondition("amount > 50000", { amount: "lots" }), null);
  assert.equal(evalCondition("amount > 50000", {}), null);
  assert.equal(evalCondition("region == EU", { region: "EU" }), true);
  assert.equal(evalCondition("region != 'EU'", { region: "US" }), true);
  assert.equal(evalCondition("flag == True", { flag: true }), true);
  assert.equal(evalCondition("garbage", { x: 1 }), null);
});

test("hash is stable and version is a string", () => {
  const c = Covenant.fromYamlString("agent: a\nversion: 2\nrules:\n  - permit: x\n");
  assert.equal(c.version, "2");
  assert.equal(c.hash, Covenant.fromObject({ agent: "a", version: 2, rules: [{ permit: "x" }] }).hash);
  assert.notEqual(c.hash, Covenant.fromYamlString("agent: a\nversion: 2\nrules:\n  - forbid: x\n").hash);
});

test("differential: the Python SDK computes the same covenant hash and decisions", { skip: !hasAirSdk() && "air_blackbox SDK not importable" }, () => {
  const c = Covenant.fromYamlString(YAML);
  const out = python(`
import json
from air_blackbox.gate.covenant import Covenant
c = Covenant.from_yaml_string(${JSON.stringify(YAML)})
cases = [("read_credit_score", {}), ("unknown_action", {}), ("approve_loan", {"amount": 75000}), ("approve_loan", {"amount": 1000}),
         ("approve_loan", {"amount": "1,000,000"}), ("approve_loan", {}), ("delete_records", {}), ("send_email", {}),
         ("send_email", {"human_approved": True}), ("list_files", {"category": "readonly"}), ("delete_records", {"category": "readonly"})]
print(json.dumps({"hash": c.hash, "decisions": [c.evaluate(a, ctx).value for a, ctx in cases]}))`);
  const theirs = JSON.parse(out) as { hash: string; decisions: string[] };
  assert.equal(c.hash, theirs.hash);
  const ours = [
    c.evaluate("read_credit_score"), c.evaluate("unknown_action"), c.evaluate("approve_loan", { amount: 75000 }),
    c.evaluate("approve_loan", { amount: 1000 }), c.evaluate("approve_loan", { amount: "1,000,000" }), c.evaluate("approve_loan"),
    c.evaluate("delete_records"), c.evaluate("send_email"), c.evaluate("send_email", { human_approved: true }),
    c.evaluate("list_files", { category: "readonly" }), c.evaluate("delete_records", { category: "readonly" }),
  ];
  assert.deepEqual(ours, theirs.decisions);
});
