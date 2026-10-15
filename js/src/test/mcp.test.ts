import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import { Covenant } from "../covenant.js";
import { airMcpClient, CovenantViolation } from "../hooks/mcp.js";
import { record } from "../recorder.js";
import { tmpdir } from "./helpers.js";

function records(dir: string): Array<Record<string, any>> {
  return fs.readdirSync(dir).filter((f) => f.endsWith(".air.json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as Record<string, any>)
    .sort((a, b) => a["chain_seq"] - b["chain_seq"]);
}

async function pair(): Promise<{ client: Client; calls: string[] }> {
  const calls: string[] = [];
  const server = new McpServer({ name: "test-server", version: "1.0.0" });
  server.registerTool("lookup_order", { inputSchema: { id: z.string() } }, async ({ id }) => {
    calls.push(`lookup_order:${id}`);
    return { content: [{ type: "text", text: JSON.stringify({ id, total: 40 }) }] };
  });
  server.registerTool("send_email", { inputSchema: { to: z.string() } }, async ({ to }) => {
    calls.push(`send_email:${to}`);
    return { content: [{ type: "text", text: "sent" }] };
  });
  server.registerTool("broken", {}, async () => ({ content: [{ type: "text", text: "upstream failed" }], isError: true }));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "agent", version: "1.0.0" });
  await client.connect(ct);
  return { client, calls };
}

const covenant = Covenant.fromYamlString("agent: a\nrules:\n  - permit: lookup_order\n  - permit: broken\n  - forbid: send_email\n");

test("records every tool call with the server's tool names", async () => {
  const dir = tmpdir();
  const rec = record("mcp-agent", { runsDir: dir, anchor: false, covenant });
  const { client, calls } = await pair();
  airMcpClient(client, rec, { server: "test-server" });
  const r = await client.callTool({ name: "lookup_order", arguments: { id: "991" } });
  assert.equal((r.content as Array<{ text: string }>)[0]!.text, JSON.stringify({ id: "991", total: 40 }));
  const e = await client.callTool({ name: "broken" });
  assert.equal(e.isError, true);
  assert.deepEqual(calls, ["lookup_order:991"]);
  const recs = records(dir);
  assert.deepEqual(recs.map((x) => [x["action"], x["status"]]), [["lookup_order", "success"], ["broken", "error"]]);
  assert.equal(recs[0]!["framework"], "mcp");
  assert.match(recs[1]!["context"]["error"], /upstream failed/);
  assert.equal(rec.verify().intact, true);
  await client.close();
});

test("enforce: a forbidden tool never reaches the server", async () => {
  const dir = tmpdir();
  const rec = record("mcp-agent", { runsDir: dir, anchor: false, covenant });
  const { client, calls } = await pair();
  airMcpClient(client, rec, { enforce: true });
  await assert.rejects(() => client.callTool({ name: "send_email", arguments: { to: "x@example.com" } }), (e: unknown) => e instanceof CovenantViolation);
  assert.deepEqual(calls, []);
  await client.callTool({ name: "lookup_order", arguments: { id: "1" } });
  assert.deepEqual(calls, ["lookup_order:1"]);
  const recs = records(dir);
  assert.deepEqual(recs.map((x) => x["status"]), ["blocked", "success"]);
  await client.close();
});
