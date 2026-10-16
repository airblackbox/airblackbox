/**
 * OpenAI Agents SDK hook: a tracing processor that records every tool
 * execution, model call, handoff and guardrail the SDK traces.
 *
 *     import { Agent, run } from "@openai/agents";
 *     import { record } from "air-blackbox";
 *     import { installAirTracing } from "air-blackbox/openai-agents";
 *
 *     const rec = record("triage-agent", { covenant: "covenant.yaml" });
 *     await installAirTracing(rec);
 *     const result = await run(agent, "Refund order 991");
 *     await rec.export();
 *
 * Tracing processors observe; they run after the fact and cannot stop a
 * tool. Each function span is still evaluated against the covenant and the
 * decision is written on its record, so a tool that ran against policy
 * shows up as such. To stop such tools before they run, wrap their execute
 * with `airTool` below.
 */
import type { Span, Trace, TracingProcessor } from "@openai/agents";

import type { Recorder } from "../recorder.js";
import { ActionGate, CovenantViolation } from "./common.js";

// Function spans of calls airTool refused, per recorder. airTool records the
// blocked attempt itself, so the processor skips these spans rather than
// record the refusal a second time as a call that ran.
const refusedSpans = new WeakMap<Recorder, Set<string>>();

export interface OpenAiAgentsOptions {
  detailLimit?: number;
  /** Also record agent spans (name, tools, handoffs) as `agent_run`. Default true. */
  agentSpans?: boolean;
}

function parseMaybeJson(s: unknown): unknown {
  if (typeof s !== "string") return s;
  try {
    return JSON.parse(s);
  } catch {
    return s;
  }
}

function durationMs(span: Span<any>): number | undefined {
  const a = span.startedAt;
  const b = span.endedAt;
  if (!a || !b) return undefined;
  return Math.max(0, Date.parse(b) - Date.parse(a));
}

export class AirTraceProcessor implements TracingProcessor {
  private readonly gate: ActionGate;
  private readonly agentSpans: boolean;

  constructor(recorder: Recorder, options: OpenAiAgentsOptions = {}) {
    this.gate = new ActionGate(recorder, { framework: "openai-agents", detailLimit: options.detailLimit });
    this.agentSpans = options.agentSpans ?? true;
  }

  async onTraceStart(_trace: Trace): Promise<void> {}
  async onTraceEnd(_trace: Trace): Promise<void> {}
  async onSpanStart(_span: Span<any>): Promise<void> {}

  async onSpanEnd(span: Span<any>): Promise<void> {
    // A tracing processor that throws must not disturb the run it observes.
    try {
      this.record(span);
    } catch (e) {
      this.gate.recorder.reportRecordError(e);
    }
  }

  private record(span: Span<any>): void {
    const d = span.spanData as Record<string, unknown> & { type: string };
    const err = span.error;
    const ms = durationMs(span);
    switch (d.type) {
      case "function": {
        if (refusedSpans.get(this.gate.recorder)?.delete(span.spanId)) return;
        const input = parseMaybeJson(d["input"]);
        const output = parseMaybeJson(d["output"]);
        this.gate.after({
          name: String(d["name"] ?? "tool"),
          input,
          output: err ? undefined : output,
          status: err ? "error" : "success",
          error: err ? err.message : undefined,
          durationMs: ms,
        });
        return;
      }
      case "generation": {
        const usage = (d["usage"] ?? {}) as Record<string, unknown>;
        this.gate.model({
          model: String(d["model"] ?? "unknown"),
          promptTokens: num(usage["input_tokens"]),
          completionTokens: num(usage["output_tokens"]),
          durationMs: ms,
          status: err ? "error" : "success",
          error: err ? err.message : undefined,
          toolCalls: toolCallNames(d["output"]),
        });
        return;
      }
      case "response": {
        // The Responses API path: the SDK keeps the raw response here.
        const resp = (d["_response"] ?? {}) as Record<string, unknown>;
        const usage = (resp["usage"] ?? {}) as Record<string, unknown>;
        this.gate.model({
          model: String(resp["model"] ?? "unknown"),
          promptTokens: num(usage["input_tokens"]),
          completionTokens: num(usage["output_tokens"]),
          totalTokens: num(usage["total_tokens"]),
          durationMs: ms,
          status: err ? "error" : "success",
          error: err ? err.message : undefined,
          toolCalls: toolCallNames(resp["output"]),
        });
        return;
      }
      case "handoff":
        this.gate.recorder.observe("handoff", {
          framework: "openai-agents",
          from_agent: d["from_agent"] ?? "",
          to_agent: d["to_agent"] ?? "",
          status: err ? "error" : "success",
        });
        return;
      case "guardrail":
        this.gate.recorder.observe("guardrail", {
          framework: "openai-agents",
          name: d["name"] ?? "",
          triggered: !!d["triggered"],
          status: err ? "error" : "success",
        });
        return;
      case "agent":
        if (this.agentSpans) {
          this.gate.recorder.observe("agent_run", {
            framework: "openai-agents",
            agent: d["name"] ?? "",
            tools: d["tools"] ?? [],
            handoffs: d["handoffs"] ?? [],
            duration_ms: Math.round(ms ?? 0),
            status: err ? "error" : "success",
          });
        }
        return;
      default:
        return;
    }
  }

  async shutdown(_timeout?: number): Promise<void> {}
  async forceFlush(): Promise<void> {}
}

function num(v: unknown): number | undefined {
  return typeof v === "number" ? v : undefined;
}

function toolCallNames(output: unknown): string[] {
  if (!Array.isArray(output)) return [];
  const names: string[] = [];
  for (const item of output) {
    if (!item || typeof item !== "object") continue;
    const o = item as Record<string, unknown>;
    if ((o["type"] === "function_call" || o["type"] === "tool_call") && typeof o["name"] === "string") names.push(o["name"]);
    const calls = o["tool_calls"];
    if (Array.isArray(calls)) {
      for (const c of calls) {
        const fn = (c as Record<string, unknown>)["function"] as Record<string, unknown> | undefined;
        if (fn && typeof fn["name"] === "string") names.push(fn["name"]);
      }
    }
  }
  return names;
}

/** Register the processor with the SDK's global tracing. */
export async function installAirTracing(recorder: Recorder, options: OpenAiAgentsOptions = {}): Promise<AirTraceProcessor> {
  const agents = await import("@openai/agents");
  const processor = new AirTraceProcessor(recorder, options);
  agents.addTraceProcessor(processor);
  return processor;
}

/**
 * Wrap a tool's execute so the covenant is enforced before it runs. Use on
 * the `execute` you pass to `tool({...})`:
 *
 *     tool({ name: "issue_refund", execute: airTool("issue_refund", rec, async (args) => ...) })
 *
 * The tracing processor records the execution; this only stops it when the
 * covenant says so, recording the blocked attempt. The refusal is returned
 * to the model as the tool's result: thrown, it would reach the model as the
 * SDK's generic "An error occurred while running the tool. Please try
 * again.", which invites the model to retry.
 */
export function airTool<A extends unknown[], R>(
  name: string,
  recorder: Recorder,
  execute: (...args: A) => R,
  options: { detailLimit?: number } = {},
): (...args: A) => R | Promise<string> {
  const gate = new ActionGate(recorder, { framework: "openai-agents", enforce: true, detailLimit: options.detailLimit });
  return (...args: A): R | Promise<string> => {
    try {
      gate.before(name, args[0]);
    } catch (e) {
      if (!(e instanceof CovenantViolation)) throw e;
      return refuse(recorder, e);
    }
    return execute(...args);
  };
}

async function refuse(recorder: Recorder, violation: CovenantViolation): Promise<string> {
  try {
    const { getCurrentSpan } = await import("@openai/agents");
    const id = getCurrentSpan()?.spanId;
    if (id && id !== "no-op") {
      let ids = refusedSpans.get(recorder);
      if (!ids) refusedSpans.set(recorder, (ids = new Set()));
      ids.add(id);
    }
  } catch {
    // No tracing to de-duplicate against.
  }
  return violation.message;
}

export { CovenantViolation } from "./common.js";
