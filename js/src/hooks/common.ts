/**
 * What every framework hook shares: turning an observed model call or tool
 * execution into a record, and, where the framework lets us intervene,
 * stopping a tool the covenant does not permit before it runs.
 */
import { hashPayload } from "../receipt.js";
import type { Recorder } from "../recorder.js";
import type { Context, RuleAction } from "../covenant.js";

/** Thrown by an enforcing hook when the covenant does not permit a tool. */
export class CovenantViolation extends Error {
  readonly action: string;
  readonly decision: RuleAction;
  constructor(action: string, decision: RuleAction) {
    super(
      decision === "require_approval"
        ? `AIR Blackbox: "${action}" requires human approval under the covenant and was not run`
        : `AIR Blackbox: "${action}" is forbidden by the covenant and was not run`,
    );
    this.name = "CovenantViolation";
    this.action = action;
    this.decision = decision;
  }
}

export interface ActionGateOptions {
  /** Name of the framework the hook serves; stored on every record. */
  framework: string;
  /**
   * Stop tools the covenant does not permit (forbid, or require_approval
   * with no approver) by throwing CovenantViolation before they run. Needs a
   * covenant on the recorder; without one every tool is permitted. Only the
   * hooks that sit in the execution path can enforce; the others observe.
   */
  enforce?: boolean;
  /** Characters of the tool input kept in the record's detail. Default 500. */
  detailLimit?: number;
}

export interface ToolObservation {
  name: string;
  input?: unknown;
  output?: unknown;
  status: "success" | "error";
  error?: string;
  durationMs?: number;
  toolCallId?: string;
  /** Extra values for the covenant's guards (not stored). */
  guard?: Context;
}

export interface ModelObservation {
  model: string;
  provider?: string;
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  durationMs?: number;
  status: "success" | "error";
  error?: string;
  /** Names of the tools the model asked to call. */
  toolCalls?: string[];
  stream?: boolean;
}

function guardFields(input: unknown): Context {
  return input && typeof input === "object" && !Array.isArray(input) ? { ...(input as Context) } : {};
}

function describe(input: unknown, limit: number): string {
  if (input === undefined || limit <= 0) return "";
  let s: string;
  try {
    s = typeof input === "string" ? input : JSON.stringify(input);
  } catch {
    s = String(input);
  }
  return s.length > limit ? s.slice(0, limit) + "…" : s;
}

export class ActionGate {
  readonly recorder: Recorder;
  readonly framework: string;
  readonly enforce: boolean;
  private readonly detailLimit: number;

  constructor(recorder: Recorder, options: ActionGateOptions) {
    this.recorder = recorder;
    this.framework = options.framework;
    this.enforce = options.enforce ?? false;
    this.detailLimit = options.detailLimit ?? 500;
  }

  /** The covenant's decision for a tool, without recording anything. */
  decide(name: string, input: unknown, guard?: Context): RuleAction {
    if (!this.recorder.covenant) return "permit";
    return this.recorder.covenant.evaluate(name, { ...guardFields(input), ...(guard ?? {}) });
  }

  /**
   * Call before a tool runs. When enforcing and the covenant does not permit
   * it, the attempt is recorded as blocked and CovenantViolation is thrown.
   */
  before(name: string, input: unknown, guard?: Context): RuleAction {
    const decision = this.decide(name, input, guard);
    if (this.enforce && decision !== "permit") {
      this.recorder.action(name, describe(input, this.detailLimit), {
        status: "blocked",
        framework: this.framework,
        guard: { ...guardFields(input), ...(guard ?? {}) },
        context: { input_hash: input === undefined ? "" : hashPayload(input), blocked_by: "covenant" },
      });
      throw new CovenantViolation(name, decision);
    }
    return decision;
  }

  /** Call after a tool ran (or failed). */
  after(obs: ToolObservation): void {
    const context: Context = {};
    if (obs.input !== undefined) context["input_hash"] = hashPayload(obs.input);
    if (obs.output !== undefined) context["output_hash"] = hashPayload(obs.output);
    if (obs.durationMs !== undefined) context["duration_ms"] = Math.round(obs.durationMs);
    if (obs.toolCallId) context["tool_call_id"] = obs.toolCallId;
    if (obs.error) context["error"] = obs.error.slice(0, 500);
    this.recorder.action(obs.name, describe(obs.input, this.detailLimit), {
      status: obs.status,
      framework: this.framework,
      guard: { ...guardFields(obs.input), ...(obs.guard ?? {}) },
      context,
    });
  }

  /** Record a model call the hook observed. */
  model(obs: ModelObservation): void {
    const tokens: Record<string, number> = {};
    if (obs.promptTokens !== undefined) tokens["prompt"] = obs.promptTokens;
    if (obs.completionTokens !== undefined) tokens["completion"] = obs.completionTokens;
    const total = obs.totalTokens ?? (obs.promptTokens !== undefined || obs.completionTokens !== undefined
      ? (obs.promptTokens ?? 0) + (obs.completionTokens ?? 0)
      : undefined);
    if (total !== undefined) tokens["total"] = total;
    const fields: Record<string, unknown> = {
      framework: this.framework,
      model: obs.model,
      provider: obs.provider ?? guessProvider(obs.model),
      tokens,
      duration_ms: Math.round(obs.durationMs ?? 0),
      status: obs.status,
    };
    if (obs.error) fields["error"] = obs.error.slice(0, 500);
    if (obs.toolCalls && obs.toolCalls.length) fields["tool_calls"] = obs.toolCalls;
    if (obs.stream) fields["stream"] = true;
    this.recorder.observe("llm_call", fields);
  }
}

/** Provider from a model name, as the gateway infers it. */
export function guessProvider(model: string): string {
  const m = model.toLowerCase();
  if (/^(gpt|o1|o3|o4|chatgpt|dall-e|text-embedding)/.test(m)) return "openai";
  if (m.startsWith("claude")) return "anthropic";
  if (m.startsWith("gemini")) return "google";
  if (/^(mistral|mixtral|codestral|pixtral)/.test(m)) return "mistral";
  if (/^(llama|meta-llama)/.test(m)) return "meta";
  if (m.startsWith("deepseek")) return "deepseek";
  if (m.startsWith("grok")) return "xai";
  if (/^(command|embed-|rerank-)/.test(m)) return "cohere";
  if (m.startsWith("qwen")) return "alibaba";
  return "unknown";
}

export function elapsedMs(start: number): number {
  return performance.now() - start;
}

export function errorText(e: unknown): string {
  return e instanceof Error ? `${e.name}: ${e.message}` : String(e);
}
