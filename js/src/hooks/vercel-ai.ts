/**
 * Vercel AI SDK hook: a language-model middleware that records every model
 * call, and a tool wrapper that records every tool execution and can stop
 * the ones the covenant does not permit.
 *
 *     import { generateText, wrapLanguageModel } from "ai";
 *     import { record } from "air-blackbox";
 *     import { airMiddleware, airTools } from "air-blackbox/vercel-ai";
 *
 *     const rec = record("support-agent", { covenant: "covenant.yaml" });
 *     const model = wrapLanguageModel({ model: openai("gpt-4o"), middleware: airMiddleware(rec) });
 *     const tools = airTools({ issueRefund, lookupOrder }, rec, { enforce: true });
 *     const result = await generateText({ model, tools, prompt });
 *     await rec.export();
 *
 * A forbidden tool is recorded as blocked and its execute throws
 * CovenantViolation, which the SDK returns to the model as a tool error.
 */
import type { LanguageModelMiddleware, ToolSet } from "ai";

import type { Recorder } from "../recorder.js";
import { ActionGate, elapsedMs, errorText } from "./common.js";

type WrapGenerate = NonNullable<LanguageModelMiddleware["wrapGenerate"]>;
type WrapStream = NonNullable<LanguageModelMiddleware["wrapStream"]>;
type GenerateResult = Awaited<ReturnType<WrapGenerate>>;
type StreamResult = Awaited<ReturnType<WrapStream>>;
type StreamPart = StreamResult["stream"] extends ReadableStream<infer P> ? P : never;
type Usage = GenerateResult["usage"];

export interface VercelAiOptions {
  enforce?: boolean;
  detailLimit?: number;
}

/**
 * Token counts from either usage shape: AI SDK 6+ reports
 * `{ inputTokens: { total }, outputTokens: { total } }`, AI SDK 5 reports
 * plain numbers `{ inputTokens, outputTokens }`.
 */
function tokens(usage: Usage | undefined): { promptTokens?: number; completionTokens?: number } {
  const out: { promptTokens?: number; completionTokens?: number } = {};
  const u = usage as unknown as { inputTokens?: number | { total?: number }; outputTokens?: number | { total?: number } } | undefined;
  const pick = (v: number | { total?: number } | undefined): number | undefined =>
    typeof v === "number" ? v : typeof v?.total === "number" ? v.total : undefined;
  const i = pick(u?.inputTokens);
  const o = pick(u?.outputTokens);
  if (i !== undefined) out.promptTokens = i;
  if (o !== undefined) out.completionTokens = o;
  return out;
}

/** Middleware that records each generate/stream call as an `llm_call`. */
export function airMiddleware(recorder: Recorder, options: VercelAiOptions = {}): LanguageModelMiddleware {
  const gate = new ActionGate(recorder, { framework: "vercel-ai", ...options });
  return {
    wrapGenerate: async ({ doGenerate, model }) => {
      const start = performance.now();
      try {
        const result = await doGenerate();
        gate.model({
          model: model.modelId,
          provider: model.provider,
          ...tokens(result.usage),
          durationMs: elapsedMs(start),
          status: "success",
          toolCalls: result.content.filter((c) => c.type === "tool-call").map((c) => (c as { toolName: string }).toolName),
        });
        return result;
      } catch (e) {
        gate.model({ model: model.modelId, provider: model.provider, durationMs: elapsedMs(start), status: "error", error: errorText(e) });
        throw e;
      }
    },
    wrapStream: async ({ doStream, model }) => {
      const start = performance.now();
      let result: StreamResult;
      try {
        result = await doStream();
      } catch (e) {
        gate.model({ model: model.modelId, provider: model.provider, durationMs: elapsedMs(start), status: "error", error: errorText(e), stream: true });
        throw e;
      }
      let usage: Usage | undefined;
      const toolCalls: string[] = [];
      let failed: string | undefined;
      const observe = new TransformStream<StreamPart, StreamPart>({
        transform(part, controller) {
          if (part.type === "finish") usage = part.usage;
          else if (part.type === "tool-call") toolCalls.push(part.toolName);
          else if (part.type === "error") failed = errorText(part.error);
          controller.enqueue(part);
        },
        flush() {
          gate.model({
            model: model.modelId,
            provider: model.provider,
            ...tokens(usage),
            durationMs: elapsedMs(start),
            status: failed ? "error" : "success",
            error: failed,
            toolCalls,
            stream: true,
          });
        },
      });
      return { ...result, stream: result.stream.pipeThrough(observe) };
    },
  };
}

function isAsyncIterable(v: unknown): v is AsyncIterable<unknown> {
  return !!v && typeof v === "object" && Symbol.asyncIterator in (v as object);
}

/**
 * Wrap a tool set so every execution is recorded as an `agent_action` with a
 * signed receipt. With `enforce`, a tool the covenant does not permit is
 * recorded as blocked and never runs. Tools without `execute` (provider-run
 * or client-side tools) pass through unchanged.
 */
export function airTools<T extends ToolSet>(tools: T, recorder: Recorder, options: VercelAiOptions = {}): T {
  const gate = new ActionGate(recorder, { framework: "vercel-ai", ...options });
  const wrapped: Record<string, unknown> = {};
  for (const [name, tool] of Object.entries(tools)) {
    const execute = tool.execute as ((input: unknown, opts: unknown) => unknown) | undefined;
    if (!execute) {
      wrapped[name] = tool;
      continue;
    }
    wrapped[name] = {
      ...tool,
      execute: async (input: unknown, opts: { toolCallId?: string }) => {
        gate.before(name, input);
        const start = performance.now();
        try {
          const out = await execute.call(tool, input, opts);
          if (isAsyncIterable(out)) {
            // Streaming tool output: record once the iteration completes.
            const src = out;
            return (async function* () {
              let last: unknown;
              try {
                for await (const chunk of src) {
                  last = chunk;
                  yield chunk;
                }
                gate.after({ name, input, output: last, status: "success", durationMs: elapsedMs(start), toolCallId: opts?.toolCallId });
              } catch (e) {
                gate.after({ name, input, status: "error", error: errorText(e), durationMs: elapsedMs(start), toolCallId: opts?.toolCallId });
                throw e;
              }
            })();
          }
          gate.after({ name, input, output: out, status: "success", durationMs: elapsedMs(start), toolCallId: opts?.toolCallId });
          return out;
        } catch (e) {
          gate.after({ name, input, status: "error", error: errorText(e), durationMs: elapsedMs(start), toolCallId: opts?.toolCallId });
          throw e;
        }
      },
    };
  }
  return wrapped as T;
}

/** Both pieces at once. */
export function withAir(recorder: Recorder, options: VercelAiOptions = {}): {
  middleware: LanguageModelMiddleware;
  tools: <T extends ToolSet>(tools: T) => T;
} {
  return { middleware: airMiddleware(recorder, options), tools: (t) => airTools(t, recorder, options) };
}

export { CovenantViolation } from "./common.js";
