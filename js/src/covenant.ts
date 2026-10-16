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

import { RawNumber, pythonJson } from "./canonical.js";
import { loadPythonYaml, pyStr as loadedStr, pyTruthy, type PyValue } from "./pyyaml.js";

export type RuleAction = "permit" | "forbid" | "require_approval";
const RULE_ACTIONS: RuleAction[] = ["permit", "forbid", "require_approval"];

export interface RuleInit {
  action: RuleAction;
  target: string;
  when?: string;
  unless?: string;
  category?: string;
  /**
   * The rule's values exactly as loaded (YAML gives ints, floats, booleans),
   * hashed as the Python SDK hashes them. Omitted for rules built in code.
   */
  raw?: { target: PyValue; when?: PyValue; unless?: PyValue; category?: PyValue };
}

export type Context = Record<string, unknown>;

/** A context's own value for a key (never an inherited member like `constructor`). */
function own(context: Context, key: string): unknown {
  return Object.prototype.hasOwnProperty.call(context, key) ? context[key] : undefined;
}

export class Rule {
  readonly action: RuleAction;
  readonly target: string;
  readonly when?: string;
  readonly unless?: string;
  readonly category?: string;
  private readonly raw?: RuleInit["raw"];

  constructor(init: RuleInit) {
    this.action = init.action;
    this.target = init.target;
    if (init.when != null) this.when = init.when;
    if (init.unless != null) this.unless = init.unless;
    if (init.category != null) this.category = init.category;
    if (init.raw) this.raw = init.raw;
  }

  matches(actionName: string, context: Context = {}): boolean {
    // A target YAML loaded as a number or boolean never equals an action
    // name, as in Python (`"1" == 1` is False).
    if (this.raw && typeof this.raw.target !== "string") return false;
    if (this.target === "*") return true;
    if (actionName === this.target) return true;
    return !!(this.category && own(context, "category") === this.category);
  }

  /**
   * Tri-state guard: true (satisfied), false (definitively not), or null
   * (indeterminate: missing field, unparseable condition, ordering on a
   * non-number). Indeterminate never opens the gate and never drops a forbid.
   */
  conditionState(context: Context = {}): boolean | null {
    if (this.unless && own(context, this.unless)) return false;
    if (!this.when) return true;
    return evalCondition(this.when, context);
  }

  toDict(): Record<string, unknown> {
    if (this.raw) {
      const d: Record<string, unknown> = { [this.action]: this.raw.target };
      if (pyTruthy(this.raw.when)) d["when"] = this.raw.when;
      if (pyTruthy(this.raw.unless)) d["unless"] = this.raw.unless;
      if (pyTruthy(this.raw.category)) d["category"] = this.raw.category;
      return d;
    }
    const d: Record<string, unknown> = { [this.action]: this.target };
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
  private readonly rawFields: { agent: unknown; description: unknown };

  constructor(init: { agent: string; version?: string | number; rules?: Rule[]; description?: string; raw?: { agent: unknown; description: unknown } }) {
    this.agent = init.agent;
    this.version = init.version == null ? "1.0" : String(init.version);
    this.rules = init.rules ?? [];
    this.description = init.description ?? "";
    this.rawFields = init.raw ?? { agent: this.agent, description: this.description };
  }

  static fromYaml(path: string): Covenant {
    return Covenant.fromYamlString(fs.readFileSync(path, "utf8"));
  }

  /** Parse YAML as the Python SDK's yaml.safe_load does, so the hash matches. */
  static fromYamlString(content: string): Covenant {
    const data = loadPythonYaml(content);
    const isMapping = data !== null && typeof data === "object" && !Array.isArray(data) && !(data instanceof RawNumber);
    return Covenant.fromObject(isMapping ? (data as Record<string, unknown>) : {});
  }

  static fromObject(data: Record<string, unknown>): Covenant {
    const rules: Rule[] = [];
    const rawRules = data["rules"];
    for (const raw of Array.isArray(rawRules) ? (rawRules as Record<string, PyValue>[]) : []) {
      for (const action of RULE_ACTIONS) {
        if (raw && typeof raw === "object" && Object.prototype.hasOwnProperty.call(raw, action)) {
          rules.push(
            new Rule({
              action,
              target: loadedStr(raw[action]),
              when: optString(raw["when"]),
              unless: optString(raw["unless"]),
              category: optString(raw["category"]),
              raw: { target: raw[action] ?? null, when: raw["when"], unless: raw["unless"], category: raw["category"] },
            }),
          );
          break;
        }
      }
    }
    const has = (k: string): boolean => Object.prototype.hasOwnProperty.call(data, k);
    const agent = has("agent") ? data["agent"] : "unknown";
    const description = has("description") ? data["description"] : "";
    return new Covenant({
      agent: typeof agent === "string" ? agent : loadedStr(agent as PyValue),
      // Python: str(data.get("version", "1.0")), so YAML's 1.0 stays "1.0".
      version: has("version") ? loadedStr(data["version"] as PyValue) : "1.0",
      rules,
      description: typeof description === "string" ? description : loadedStr(description as PyValue),
      raw: { agent, description },
    });
  }

  /**
   * Context fields only the application may supply: each rule's `unless`
   * field (e.g. human_approved) and `category`. The framework hooks keep
   * tool arguments, which the model writes, out of these.
   */
  appOnlyFields(): Set<string> {
    const fields = new Set<string>(["category"]);
    for (const rule of this.rules) if (rule.unless) fields.add(rule.unless);
    return fields;
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
      agent: this.rawFields.agent,
      version: this.version,
      description: this.rawFields.description,
      rules: this.rules.map((r) => r.toDict()),
    };
  }

  /** SHA-256 of the canonical covenant; identical to the Python SDK's. */
  get hash(): string {
    return createHash("sha256").update(pythonJson(this.toDict()), "utf8").digest("hex");
  }
}

function optString(v: unknown): string | undefined {
  return v == null ? undefined : typeof v === "string" ? v : loadedStr(v as PyValue);
}

/**
 * "field op value" to a tri-state, mirroring the Python `_eval_condition`:
 * numeric comparison when both sides parse as numbers; otherwise only == and
 * != are meaningful and an ordering comparison is indeterminate.
 */
export function evalCondition(condition: string, context: Context): boolean | null {
  // Python's re.match(r"(\w+)\s*(op)\s*(.+)"): anchored at the start only, and
  // the value runs from the first non-space character to the end of the line.
  // \s and \S don't overlap, so the match can't backtrack quadratically.
  const m = /^(\w+)\s*(>=|<=|!=|==|>|<)\s*(\S[^\n]*)/.exec(condition.trim());
  if (!m) return null;
  const [, field, op, rawValue] = m;
  const want = stripChar(stripChar(rawValue!.trim(), '"'), "'");
  const got = own(context, field!);
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

/** Python str.strip(c) for a single character. */
function stripChar(s: string, c: string): string {
  let start = 0;
  let end = s.length;
  while (start < end && s[start] === c) start++;
  while (end > start && s[end - 1] === c) end--;
  return s.slice(start, end);
}

// Python float() syntax: digits may be separated by single underscores. Each
// repetition consumes exactly one digit, so matching is linear (context values
// can come from tool arguments a model wrote).
const DIGITS = String.raw`\d(?:_?\d)*`;
const DECIMAL = new RegExp(`^[+-]?(?:${DIGITS}(?:\\.(?:${DIGITS})?)?|\\.${DIGITS})(?:[eE][+-]?${DIGITS})?$`);
const SPECIAL = /^([+-]?)(inf|infinity|nan)$/i;

/**
 * Python float(x) semantics for the values a context can carry, or null where
 * float() would raise. NaN is a number here, as in Python: every ordering and
 * == comparison with it is false and != is true.
 */
function toNumber(v: unknown): number | null {
  if (typeof v === "number") return v;
  if (typeof v === "boolean") return v ? 1 : 0;
  if (typeof v === "string") {
    const t = v.trim();
    if (DECIMAL.test(t)) return Number(t.replace(/_/g, ""));
    const special = SPECIAL.exec(t);
    if (!special) return null;
    if (special[2]!.toLowerCase() === "nan") return NaN;
    return special[1] === "-" ? -Infinity : Infinity;
  }
  return null;
}

/** Python str() for the values a context can carry. */
function pyStr(v: unknown): string {
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(v);
  return String(v);
}
