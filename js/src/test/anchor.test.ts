import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";

import { computeHead, extractGenTime, headOverEntries, makeQuery } from "../anchor.js";
import { AuditChain } from "../chain.js";
import { hasAirSdk, hasPython, python, tmpdir } from "./helpers.js";

const hasOpenssl = spawnSync("openssl", ["version"]).status === 0;

test("head over entries is order-independent and key-free", () => {
  const a = headOverEntries([[1, "aa"], [2, "bb"]]);
  const b = headOverEntries([[2, "bb"], [1, "aa"]]);
  assert.equal(a, b);
  assert.equal(a.length, 64);
  assert.equal(headOverEntries([]), "");
  assert.notEqual(a, headOverEntries([[1, "aa"], [2, "bc"]]));
});

test("computeHead reads a runs directory and honours the sequence bound", () => {
  const dir = tmpdir();
  const chain = new AuditChain(dir, "k");
  chain.write({ type: "x" });
  const h1 = computeHead(dir);
  chain.write({ type: "y" });
  const h2 = computeHead(dir);
  assert.notEqual(h1, h2);
  assert.equal(computeHead(dir, 1), h1);
});

test("the timestamp query is a well-formed RFC 3161 request", { skip: !hasOpenssl && "openssl not available" }, () => {
  const head = "ab".repeat(32);
  const tsq = makeQuery(head);
  const dir = tmpdir();
  const file = path.join(dir, "req.tsq");
  fs.writeFileSync(file, tsq);
  const r = spawnSync("openssl", ["ts", "-query", "-in", file, "-text"], { encoding: "utf8" });
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /Version: 1/);
  assert.match(r.stdout, /sha256/i);
  assert.match(r.stdout, /Certificate required: yes/i);
  // openssl prints the imprint as a hex dump; check the digest bytes via the DER instead.
  const der = spawnSync("openssl", ["asn1parse", "-inform", "DER", "-in", file], { encoding: "utf8" });
  assert.equal(der.status, 0, der.stderr);
  assert.match(der.stdout, new RegExp(`OCTET STRING\\s+\\[HEX DUMP\\]:${head.toUpperCase()}`));
});

test("genTime is extracted from a timestamp response built by openssl", { skip: !hasOpenssl && "openssl not available" }, () => {
  // Build a self-signed TSA and answer our own query, entirely offline.
  const dir = tmpdir();
  const run = (args: string[]): void => {
    const r = spawnSync("openssl", args, { encoding: "utf8", cwd: dir });
    assert.equal(r.status, 0, `${args.join(" ")}: ${r.stderr}`);
  };
  fs.writeFileSync(path.join(dir, "tsa.cnf"), [
    "[req]", "distinguished_name = dn", "x509_extensions = ext", "prompt = no",
    "[dn]", "CN = test tsa",
    "[ext]", "extendedKeyUsage = critical,timeStamping", "keyUsage = digitalSignature",
    "[tsa]", "default_tsa = tsa_config",
    "[tsa_config]", `dir = ${dir}`, "serial = $dir/serial", "signer_cert = $dir/tsa.pem", "signer_key = $dir/tsa.key",
    "signer_digest = sha256", "default_policy = 1.2.3.4", "other_policies = 1.2.3.4", "digests = sha256", "accuracy = secs:1", "ordering = yes", "tsa_name = yes", "ess_cert_id_chain = no",
  ].join("\n"));
  fs.writeFileSync(path.join(dir, "serial"), "01\n");
  run(["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "tsa.key", "-out", "tsa.pem", "-days", "1", "-config", "tsa.cnf"]);
  fs.writeFileSync(path.join(dir, "req.tsq"), makeQuery("cd".repeat(32)));
  run(["ts", "-reply", "-config", "tsa.cnf", "-queryfile", "req.tsq", "-out", "resp.tsr"]);
  const tsr = fs.readFileSync(path.join(dir, "resp.tsr"));
  const t = extractGenTime(tsr);
  assert.ok(t, "no genTime extracted");
  assert.match(t!, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/);
  // And the reply verifies against the query we built.
  run(["ts", "-verify", "-queryfile", "req.tsq", "-in", "resp.tsr", "-CAfile", "tsa.pem"]);
});

/** A throwaway RFC 3161 authority: openssl answering over HTTP. Returns its URL, CA path and a closer. */
async function localTsa(): Promise<{ url: string; ca: string; close: () => Promise<void> }> {
  const http = await import("node:http");
  const dir = tmpdir("air-tsa-");
  const run = (args: string[]): void => {
    const r = spawnSync("openssl", args, { encoding: "utf8", cwd: dir });
    if (r.status !== 0) throw new Error(`${args.join(" ")}: ${r.stderr}`);
  };
  fs.writeFileSync(path.join(dir, "tsa.cnf"), [
    "[req]", "distinguished_name = dn", "x509_extensions = ext", "prompt = no",
    "[dn]", "CN = local test tsa",
    "[ext]", "extendedKeyUsage = critical,timeStamping", "keyUsage = digitalSignature",
    "[tsa]", "default_tsa = tsa_config",
    "[tsa_config]", `dir = ${dir}`, "serial = $dir/serial", "signer_cert = $dir/tsa.pem", "signer_key = $dir/tsa.key",
    "signer_digest = sha256", "default_policy = 1.2.3.4", "digests = sha256", "accuracy = secs:1", "ordering = yes", "tsa_name = yes", "ess_cert_id_chain = no",
  ].join("\n"));
  fs.writeFileSync(path.join(dir, "serial"), "01\n");
  run(["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "tsa.key", "-out", "tsa.pem", "-days", "1", "-config", "tsa.cnf"]);
  let n = 0;
  const server = http.createServer((req, res) => {
    const chunks: Buffer[] = [];
    req.on("data", (c: Buffer) => chunks.push(c));
    req.on("end", () => {
      const id = n++;
      fs.writeFileSync(path.join(dir, `q${id}.tsq`), Buffer.concat(chunks));
      try {
        run(["ts", "-reply", "-config", "tsa.cnf", "-queryfile", `q${id}.tsq`, "-out", `r${id}.tsr`]);
        res.writeHead(200, { "Content-Type": "application/timestamp-reply" });
        res.end(fs.readFileSync(path.join(dir, `r${id}.tsr`)));
      } catch (e) {
        res.writeHead(500);
        res.end(String(e));
      }
    });
  });
  await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
  const addr = server.address() as { port: number };
  return {
    url: `http://127.0.0.1:${addr.port}/tsr`,
    ca: path.join(dir, "tsa.pem"),
    close: () => new Promise<void>((r) => server.close(() => r())),
  };
}

test("an anchored export passes the Python verifier's external-anchor check, and a rewrite fails it",
  { skip: !(hasOpenssl && hasAirSdk()) && "needs openssl and the air_blackbox SDK" }, async () => {
  const tsa = await localTsa();
  try {
    const { record } = await import("../recorder.js");
    const dir = tmpdir();
    // An unreachable authority first: the recorder must fall through to the next.
    const rec = record("anchored", { runsDir: dir, tsaUrls: ["http://127.0.0.1:9/tsr", tsa.url], anchorTimeout: 5000 });
    rec.action("read_ticket", "ticket #1");
    rec.action("issue_refund", "order 991", { humanReviewer: "dana@acme.example" });
    const bundle = await rec.export();
    assert.match(rec.lastExportNote, /^timestamped by http:\/\/127\.0\.0\.1/);
    const verify = (file: string): string => python(`
import io, json
from air_blackbox.evidence_verify import verify_bundle, VerificationFailure
buf = io.StringIO()
try:
    r = verify_bundle(${JSON.stringify(file)}, tsa_cacert=${JSON.stringify(tsa.ca)}, out=buf)
    print(json.dumps({"ok": True, "anchor": r.get("anchor"), "log": buf.getvalue()}))
except VerificationFailure as e:
    print(json.dumps({"ok": False, "error": str(e), "log": buf.getvalue()}))`);
    const good = JSON.parse(verify(bundle)) as { ok: boolean; anchor?: string; log: string; error?: string };
    assert.equal(good.ok, true, good.error ?? good.log);
    assert.match(good.log, /\[6\/6\] External anchor: VERIFIED/);

    // An operator rewrites the history after it was anchored, re-chains it,
    // re-signs everything with their own key, and reuses the genuine anchor.
    // Every signature is valid; only the external timestamp can catch it.
    const { unzipSync } = await import("fflate");
    const { generateEvidenceBundleV1 } = await import("../bundle.js");
    const { loadRecords, verifyRecords } = await import("../chain.js");
    const { ReceiptSigner } = await import("../receipt.js");
    const z = unzipSync(fs.readFileSync(bundle));
    const genuineAnchor = (JSON.parse(Buffer.from(z["manifest.json"]!).toString()) as { anchor: never }).anchor;
    const forgeDir = tmpdir();
    const rewritten = record("anchored", { runsDir: forgeDir, anchor: false });
    rewritten.action("read_ticket", "ticket #1");
    rewritten.action("issue_refund", "order 991, refund doubled");
    const records = loadRecords(forgeDir);
    const { path: forged } = generateEvidenceBundleV1({
      chainEntries: records,
      tenant: "anchored",
      signer: new ReceiptSigner({ privateKey: Buffer.from((JSON.parse(fs.readFileSync(path.join(forgeDir, ".air-receipt-key"), "utf8")) as { seed: string }).seed, "hex") }),
      chainVerification: { fully_intact: true, ...verifyRecords(records, "air-blackbox-default") },
      anchor: genuineAnchor,
      outputDir: forgeDir,
    });
    const bad = JSON.parse(verify(forged)) as { ok: boolean; error?: string; log: string };
    assert.equal(bad.ok, false, "a reused anchor over a rewritten history must not verify");
    assert.match(bad.log, /\[5\/6\] Counts: manifest matches records/, "checks 1-5 pass: the forgery is internally consistent");
    assert.match(bad.error ?? "", /imprint|does not match|rewritten/i);
  } finally {
    await tsa.close();
  }
});

test("differential: head matches the Python head_over_entries", { skip: !(hasPython() && hasAirSdk()) && "air_blackbox SDK not importable" }, () => {
  const entries: Array<[number, string]> = [[3, "cc"], [1, "aa"], [2, "bb"]];
  const theirs = python(`
from air_blackbox.anchor.head import head_over_entries
print(head_over_entries([(3, "cc"), (1, "aa"), (2, "bb")]))`).trim();
  assert.equal(headOverEntries(entries), theirs);
});
