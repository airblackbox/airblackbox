/**
 * LangChain.js / LangGraph.js hook: a callback handler that records every
 * model call and tool execution, and can stop tools the covenant does not
 * permit.
 *
 *     import { record } from "air-blackbox";
 *     import { AirCallbackHandler } from "air-blackbox/langchain";
 *
 *     const rec = record("research-agent", { covenant: "covenant.yaml" });
 *     const handler = new AirCallbackHandler(rec, { enforce: true });
 *     await chain.invoke(input, { callbacks: [handler] });
 *     await rec.export();
 *
 * With `enforce`, the handler runs synchronously ahead of each tool and
 * throws CovenantViolation from handleToolStart, which LangChain propagates
 * before the tool's function is called. Without it the handler only observes,
 * and runs in the background as LangChain callbacks normally do.
 */
import { BaseCallbackHandler } from "@langchain/core/callbacks/base";
import type { Serialized } from "@langchain/core/load/serializable";
import type { LLMResult } from "@langchain/core/outputs";
import type { BaseMessage } from "@langchain/core/messages";

import type { Recorder } from "../recorder.js";
import { ActionGate, elapsedMs, errorText } from "./common.js";

export interface LangChainOptions {
  enforce?: boolean;
  detailLimit?: number;
}

interface LlmRun {
  start: number;
  model: string;
  provider: string;
}

interface ToolRun {
  start: number;
  name: string;
  input: unknown;
  toolCallId?: string;
}

function parseMaybeJson(s: string): unknown {
  try {
    return JSON.parse(s);
  } catch {
    return s;
  }
}

function modelName(llm: Serialized, extraParams?: Record<string, unknown>): string {
  const kw = (llm as { kwargs?: Record<string, unknown> }).kwargs ?? {};
  const inv = (extraParams?.["invocation_params"] ?? {}) as Record<string, unknown>;
  for (const v of [kw["model"], kw["model_name"], kw["modelName"], inv["model"], inv["model_name"]]) {
    if (typeof v === "string" && v) return v;
  }
  const id = (llm as { id?: string[] }).id;
  return id?.[id.length - 1] ?? "unknown";
}

function providerFrom(llm: Serialized): string {
  const id = ((llm as { id?: string[] }).id ?? []).join(".").toLowerCase();
  for (const p of ["openai", "anthropic", "google", "cohere", "mistral", "ollama", "groq", "bedrock"]) {
    if (id.includes(p)) return p;
  }
  return "unknown";
}

function usageFrom(output: LLMResult): { promptTokens?: number; completionTokens?: number; totalTokens?: number } {
  const lo = (output.llmOutput ?? {}) as Record<string, unknown>;
  const tu = (lo["tokenUsage"] ?? lo["usage"] ?? lo["token_usage"]) as Record<string, unknown> | undefined;
  if (tu) {
    const n = (k: string): number | undefined => (typeof tu[k] === "number" ? (tu[k] as number) : undefined);
    const prompt = n("promptTokens") ?? n("prompt_tokens") ?? n("input_tokens") ?? n("inputTokens");
    const completion = n("completionTokens") ?? n("completion_tokens") ?? n("output_tokens") ?? n("outputTokens");
    const total = n("totalTokens") ?? n("total_tokens");
    if (prompt !== undefined || completion !== undefined || total !== undefined) return { promptTokens: prompt, completionTokens: completion, totalTokens: total };
  }
  const gen = output.generations?.[0]?.[0] as { message?: { usage_metadata?: Record<string, unknown> } } | undefined;
  const um = gen?.message?.usage_metadata;
  if (um) {
    const n = (k: string): number | undefined => (typeof um[k] === "number" ? (um[k] as number) : undefined);
    return { promptTokens: n("input_tokens"), completionTokens: n("output_tokens"), totalTokens: n("total_tokens") };
  }
  return {};
}

export class AirCallbackHandler extends BaseCallbackHandler {
  name = "air_blackbox";
  private readonly gate: ActionGate;
  private readonly llmRuns = new Map<string, LlmRun>();
  private readonly toolRuns = new Map<string, ToolRun>();

  constructor(recorder: Recorder, options: LangChainOptions = {}) {
    // raiseError makes LangChain await this handler and propagate what it
    // throws, which is what lets handleToolStart stop a tool.
    super({ raiseError: options.enforce ?? false });
    this.gate = new ActionGate(recorder, { framework: "langchain", enforce: options.enforce, detailLimit: options.detailLimit });
  }

  override handleLLMStart(llm: Serialized, _prompts: string[], runId: string, _parent?: string, extraParams?: Record<string, unknown>): void {
    this.llmRuns.set(runId, { start: performance.now(), model: modelName(llm, extraParams), provider: providerFrom(llm) });
  }

  override handleChatModelStart(llm: Serialized, _messages: BaseMessage[][], runId: string, _parent?: string, extraParams?: Record<string, unknown>): void {
    this.llmRuns.set(runId, { start: performance.now(), model: modelName(llm, extraParams), provider: providerFrom(llm) });
  }

  override handleLLMEnd(output: LLMResult, runId: string): void {
    const run = this.llmRuns.get(runId);
    this.llmRuns.delete(runId);
    const toolCalls: string[] = [];
    for (const gens of output.generations ?? []) {
      for (const g of gens) {
        const calls = (g as { message?: { tool_calls?: Array<{ name?: string }> } }).message?.tool_calls ?? [];
        for (const c of calls) if (c.name) toolCalls.push(c.name);
      }
    }
    this.gate.model({
      model: run?.model ?? "unknown",
      provider: run?.provider,
      ...usageFrom(output),
      durationMs: run ? elapsedMs(run.start) : undefined,
      status: "success",
      toolCalls,
    });
  }

  override handleLLMError(err: Error, runId: string): void {
    const run = this.llmRuns.get(runId);
    this.llmRuns.delete(runId);
    this.gate.model({ model: run?.model ?? "unknown", provider: run?.provider, durationMs: run ? elapsedMs(run.start) : undefined, status: "error", error: errorText(err) });
  }

  override handleToolStart(tool: Serialized, input: string, runId: string, _parent?: string, _tags?: string[], _metadata?: Record<string, unknown>, runName?: string, toolCallId?: string): void {
    const id = (tool as { id?: string[] }).id;
    const name = runName ?? id?.[id.length - 1] ?? "tool";
    const parsed = parseMaybeJson(input);
    this.toolRuns.set(runId, { start: performance.now(), name, input: parsed, toolCallId });
    // Throws CovenantViolation when enforcing and not permitted; LangChain
    // propagates it (raiseError) before the tool function runs.
    try {
      this.gate.before(name, parsed);
    } catch (e) {
      this.toolRuns.delete(runId);
      throw e;
    }
  }

  override handleToolEnd(output: unknown, runId: string): void {
    const run = this.toolRuns.get(runId);
    this.toolRuns.delete(runId);
    if (!run) return;
    const out = output && typeof output === "object" && "content" in (output as object) ? (output as { content: unknown }).content : output;
    this.gate.after({ name: run.name, input: run.input, output: out, status: "success", durationMs: elapsedMs(run.start), toolCallId: run.toolCallId });
  }

  override handleToolError(err: Error, runId: string): void {
    const run = this.toolRuns.get(runId);
    this.toolRuns.delete(runId);
    if (!run) return;
    this.gate.after({ name: run.name, input: run.input, status: "error", error: errorText(err), durationMs: elapsedMs(run.start), toolCallId: run.toolCallId });
  }
}

export { CovenantViolation } from "./common.js";
