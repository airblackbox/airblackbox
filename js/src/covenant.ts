/**
 * Covenant: the declarative policy an agent commits to before it acts.
 *
 * Same YAML as the Python SDK, same precedence (forbid > require_approval >
 * permit > default forbid), same fail-closed guard semantics, and the same
 * hash: SHA-256 over the canonical JSON of {agent, version, description,
 * rules}. A covenant file produces one hash whichever SDK loads it, so a
 * receipt proves which rules were active regardless of language.
 *
 *     agent: loan-processor
 *     version: "1.0"
 *     rules:
 *       - permit: read_credit_score
 *       - require_approval: approve_loan
 *         when: "amount > 50000"
 *       - forbid: delete_records
 *       - forbid: send_email
 *         unless: human_approved
 */
import { createHash } from "node:crypto";
import * as fs from "node:fs";

import { parse as parseYaml } from "yaml";

import { pythonJson } from "./canonical.js";

export type RuleAction = "permit" | "forbid" | "require_approval";
const RULE_ACTIONS: RuleAction[] = ["permit", "forbid", "require_approval"];

export interface RuleInit {
  action: RuleAction;
  target: string;
  when?: string;
  unless?: string;
  category?: string;
}

export type Context = Record<string, unknown>;

export class Rule {
  readonly action: RuleAction;
  readonly target: string;
  readonly when?: string;
  readonly unless?: string;
  readonly category?: string;

  constructor(init: RuleInit) {
    this.action = init.action;
    this.target = init.target;
    if (init.when != null) this.when = init.when;
    if (init.unless != null) this.unless = init.unless;
    if (init.category != null) this.category = init.category;
  }

  matches(actionName: string, context: Context = {}): boolean {
    if (this.target === "*") return true;
    if (actionName === this.target) return true;
    return !!(this.category && context["category"] === this.category);
  }

  /**
   * Tri-state guard: true (satisfied), false (definitively not), or null
   * (indeterminate: missing field, unparseable condition, ordering on a
   * non-number). Indeterminate never opens the gate and never drops a forbid.
   */
  conditionState(context: Context = {}): boolean | null {
    if (this.unless && context[this.unless]) return false;
    if (!this.when) return true;
    return evalCondition(this.when, context);
  }

  toDict(): Record<string, string> {
    const d: Record<string, string> = { [this.action]: this.target };
    if (this.when) d["when"] = this.when;
    if (this.unless) d["unless"] = this.unless;
    if (this.category) d["category"] = this.category;
    return d;
  }
}

export class Covenant {
  readonly agent: string;
  readonly version: string;
  readonly rules: Rule[];
  readonly description: string;

  constructor(init: { agent: string; version?: string | number; rules?: Rule[]; description?: string }) {
    this.agent = init.agent;
    this.version = init.version == null ? "1.0" : String(init.version);
    this.rules = init.rules ?? [];
    this.description = init.description ?? "";
  }

  static fromYaml(path: string): Covenant {
    return Covenant.fromYamlString(fs.readFileSync(path, "utf8"));
  }

  static fromYamlString(content: string): Covenant {
    return Covenant.fromObject(parseYaml(content) ?? {});
  }

  static fromObject(data: Record<string, unknown>): Covenant {
    const rules: Rule[] = [];
    for (const raw of (data["rules"] as Record<string, unknown>[] | undefined) ?? []) {
      for (const action of RULE_ACTIONS) {
        if (action in raw) {
          rules.push(
            new Rule({
              action,
              target: String(raw[action]),
              when: optString(raw["when"]),
              unless: optString(raw["unless"]),
              category: optString(raw["category"]),
            }),
          );
          break;
        }
      }
    }
    return new Covenant({
      agent: (data["agent"] as string | undefined) ?? "unknown",
      version: (data["version"] as string | number | undefined) ?? "1.0",
      rules,
      description: (data["description"] as string | undefined) ?? "",
    });
  }

  /** forbid > require_approval > permit > default forbid. */
  evaluate(actionName: string, context: Context = {}): RuleAction {
    const matched: Rule[] = [];
    for (const rule of this.rules) {
      if (!rule.matches(actionName, context)) continue;
      const state = rule.conditionState(context);
      if (rule.action === "forbid") {
        // Fail closed: a forbid stays active unless its guard is definitively false.
        if (state !== false) matched.push(rule);
      } else if (state === true) {
        matched.push(rule);
      }
    }
    if (matched.length === 0) return "forbid";
    if (matched.some((r) => r.action === "forbid")) return "forbid";
    if (matched.some((r) => r.action === "require_approval")) return "require_approval";
    return "permit";
  }

  toDict(): Record<string, unknown> {
    return {
      agent: this.agent,
      version: this.version,
      description: this.description,
      rules: this.rules.map((r) => r.toDict()),
    };
  }

  /** SHA-256 of the canonical covenant; identical to the Python SDK's. */
  get hash(): string {
    return createHash("sha256").update(pythonJson(this.toDict()), "utf8").digest("hex");
  }
}

function optString(v: unknown): string | undefined {
  return v == null ? undefined : String(v);
}

/**
 * "field op value" to a tri-state, mirroring the Python `_eval_condition`:
 * numeric comparison when both sides parse as numbers; otherwise only == and
 * != are meaningful and an ordering comparison is indeterminate.
 */
export function evalCondition(condition: string, context: Context): boolean | null {
  const m = /^(\w+)\s*(>=|<=|!=|==|>|<)\s*(.+)$/.exec(condition.trim());
  if (!m) return null;
  const [, field, op, rawValue] = m;
  const want = rawValue!.trim().replace(/^["']|["']$/g, "");
  const got = context[field!];
  if (got === undefined || got === null) return null;
  const gotNum = toNumber(got);
  const wantNum = toNumber(want);
  if (gotNum !== null && wantNum !== null) {
    switch (op) {
      case ">": return gotNum > wantNum;
      case "<": return gotNum < wantNum;
      case ">=": return gotNum >= wantNum;
      case "<=": return gotNum <= wantNum;
      case "==": return gotNum === wantNum;
      case "!=": return gotNum !== wantNum;
    }
  }
  const gotStr = pyStr(got);
  if (op === "==") return gotStr === want;
  if (op === "!=") return gotStr !== want;
  return null;
}

/** Python float(x) semantics for the values a context can carry. */
function toNumber(v: unknown): number | null {
  if (typeof v === "number") return Number.isNaN(v) ? null : v;
  if (typeof v === "boolean") return v ? 1 : 0;
  if (typeof v === "string") {
    const t = v.trim();
    if (t === "" || !/^[+-]?(?:\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?|inf(?:inity)?|nan)$/i.test(t)) return null;
    const n = Number(t);
    return Number.isNaN(n) ? null : n;
  }
  return null;
}

/** Python str() for the values a context can carry. */
function pyStr(v: unknown): string {
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(v);
  return String(v);
}
