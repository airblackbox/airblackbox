/**
 * Model Context Protocol hook: record every tool call an MCP client makes,
 * and stop the ones the covenant does not permit before they reach the
 * server.
 *
 *     import { Client } from "@modelcontextprotocol/sdk/client/index.js";
 *     import { record } from "air-blackbox";
 *     import { airMcpClient } from "air-blackbox/mcp";
 *
 *     const rec = record("mcp-agent", { covenant: "covenant.yaml" });
 *     const client = airMcpClient(new Client({ name: "agent", version: "1.0" }), rec, { enforce: true });
 *     await client.connect(transport);
 *     await client.callTool({ name: "send_email", arguments: { to: "..." } });
 *
 * The client's `callTool` is replaced on the instance; everything else is
 * untouched. Tool names are recorded as the server names them, so a covenant
 * rule `forbid: send_email` matches the MCP tool `send_email`.
 */
import type { Recorder } from "../recorder.js";
import { ActionGate, elapsedMs, errorText } from "./common.js";

export interface McpOptions {
  enforce?: boolean;
  detailLimit?: number;
  /** A label for the server, stored on each record. */
  server?: string;
}

interface CallToolParams {
  name: string;
  arguments?: Record<string, unknown>;
}

interface CallToolResultLike {
  content?: unknown;
  isError?: boolean;
  structuredContent?: unknown;
  [key: string]: unknown;
}

// Structural, so any SDK version's Client fits: only callTool's first
// parameter and the result's content/isError are relied on.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ClientLike = { callTool: (params: any, ...rest: any[]) => Promise<any> };

/** Patch an MCP client so its tool calls are recorded (and gated). */
export function airMcpClient<C extends ClientLike>(client: C, recorder: Recorder, options: McpOptions = {}): C {
  const gate = new ActionGate(recorder, { framework: "mcp", enforce: options.enforce, detailLimit: options.detailLimit });
  const original = client.callTool.bind(client) as (params: CallToolParams, ...rest: unknown[]) => Promise<CallToolResultLike>;
  const patched = async (params: CallToolParams, ...rest: unknown[]): Promise<CallToolResultLike> => {
    const guard = options.server ? { server: options.server } : undefined;
    gate.before(params.name, params.arguments, guard);
    const start = performance.now();
    try {
      const result = await original(params, ...rest);
      const output = result.structuredContent ?? result.content;
      gate.after({
        name: params.name,
        input: params.arguments,
        output,
        status: result.isError ? "error" : "success",
        error: result.isError ? firstText(result.content) : undefined,
        durationMs: elapsedMs(start),
        guard,
      });
      return result;
    } catch (e) {
      gate.after({ name: params.name, input: params.arguments, status: "error", error: errorText(e), durationMs: elapsedMs(start), guard });
      throw e;
    }
  };
  Object.defineProperty(client, "callTool", { value: patched, writable: true, configurable: true });
  return client;
}

function firstText(content: unknown): string | undefined {
  if (!Array.isArray(content)) return undefined;
  for (const c of content) {
    if (c && typeof c === "object" && (c as { type?: string }).type === "text") return String((c as { text?: unknown }).text ?? "").slice(0, 500);
  }
  return undefined;
}

export { CovenantViolation } from "./common.js";
