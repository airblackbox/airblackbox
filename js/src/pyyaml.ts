/**
 * Load YAML into the values PyYAML's `yaml.safe_load` would produce, so a
 * covenant hashes the same in both SDKs.
 *
 * PyYAML resolves plain scalars by YAML 1.1 rules: `on`/`off`/`yes`/`no` are
 * booleans, `1.0` is a float (Python writes it back as `1.0`, not `1`), `1e3`
 * is a string (its float pattern needs a dot and a signed exponent), `010` is
 * octal and `1:30` is 90. JavaScript YAML parsers follow 1.2 or differ in
 * those corners, so this parses structure with the `yaml` package's failsafe
 * schema (every scalar a string) and resolves plain scalars itself. Ints and
 * floats come back as RawNumber holding Python's text for them, which the
 * canonical serialiser writes verbatim.
 */
import { isAlias, isMap, isScalar, isSeq, parseDocument, type Document } from "yaml";

import { RawNumber, pythonFloatRepr } from "./canonical.js";

// PyYAML's implicit resolvers (yaml/resolver.py), anchored. Each repetition
// starts with a distinct character, so none of these can backtrack badly.
const NULL = /^(?:~|null|Null|NULL|)$/;
const TRUE = /^(?:yes|Yes|YES|true|True|TRUE|on|On|ON)$/;
const FALSE = /^(?:no|No|NO|false|False|FALSE|off|Off|OFF)$/;
const INT = /^(?:[-+]?0b[01_]+|[-+]?0[0-7_]+|[-+]?(?:0|[1-9][0-9_]*)|[-+]?0x[0-9a-fA-F_]+|[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$/;
const FLOAT = /^(?:[-+]?[0-9][0-9_]*\.[0-9_]*(?:[eE][-+][0-9]+)?|\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?|[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$/;

/** A Python value: str, bool, None, int/float (as RawNumber), list or dict. */
export type PyValue = string | boolean | null | RawNumber | PyValue[] | { [key: string]: PyValue };

export function loadPythonYaml(text: string): PyValue {
  const doc = parseDocument(text, { schema: "failsafe" });
  if (doc.errors.length) throw doc.errors[0];
  return convert(doc, doc.contents);
}

function convert(doc: Document, node: unknown): PyValue {
  if (node == null) return null;
  if (isAlias(node)) return convert(doc, node.resolve(doc));
  if (isMap(node)) {
    const out: { [key: string]: PyValue } = {};
    for (const pair of node.items) {
      Object.defineProperty(out, pyStr(convert(doc, pair.key)), {
        value: convert(doc, pair.value), enumerable: true, writable: true, configurable: true,
      });
    }
    return out;
  }
  if (isSeq(node)) return node.items.map((item) => convert(doc, item));
  if (isScalar(node)) {
    const text = String(node.value ?? "");
    if (node.type !== "PLAIN" || node.tag === "tag:yaml.org,2002:str") return text;
    return resolvePlain(text);
  }
  return null;
}

function resolvePlain(s: string): PyValue {
  if (NULL.test(s)) return null;
  if (TRUE.test(s)) return true;
  if (FALSE.test(s)) return false;
  if (INT.test(s)) return new RawNumber(pyInt(s));
  if (FLOAT.test(s)) return new RawNumber(pyFloat(s));
  return s;
}

/** PyYAML's construct_yaml_int, as exact decimal text. */
function pyInt(raw: string): string {
  let s = raw.replace(/_/g, "");
  let sign = 1n;
  if (s[0] === "-" || s[0] === "+") {
    if (s[0] === "-") sign = -1n;
    s = s.slice(1);
  }
  let n: bigint;
  if (s === "0") n = 0n;
  else if (s.startsWith("0b")) n = BigInt(s);
  else if (s.startsWith("0x")) n = BigInt(s);
  else if (s.startsWith("0")) n = BigInt("0o" + s.slice(1));
  else if (s.includes(":")) n = s.split(":").reduce((acc, part) => acc * 60n + BigInt(part), 0n);
  else n = BigInt(s);
  return (sign * n).toString();
}

/** PyYAML's construct_yaml_float, as Python's repr of the result. */
function pyFloat(raw: string): string {
  let s = raw.replace(/_/g, "").toLowerCase();
  let sign = 1;
  if (s[0] === "-" || s[0] === "+") {
    if (s[0] === "-") sign = -1;
    s = s.slice(1);
  }
  let v: number;
  if (s === ".inf") v = sign * Infinity;
  else if (s === ".nan") v = NaN;
  else if (s.includes(":")) v = sign * s.split(":").reduce((acc, part) => acc * 60 + Number(part), 0);
  else v = sign * Number(s);
  if (Number.isNaN(v)) return "NaN";
  if (!Number.isFinite(v)) return v > 0 ? "Infinity" : "-Infinity";
  return pythonFloatRepr(v);
}

/** Python's str() of a loaded value. */
export function pyStr(v: PyValue | undefined): string {
  if (v === null || v === undefined) return "None";
  if (v === true) return "True";
  if (v === false) return "False";
  if (v instanceof RawNumber) return v.text === "Infinity" ? "inf" : v.text === "-Infinity" ? "-inf" : v.text === "NaN" ? "nan" : v.text;
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}

/** Python truthiness of a loaded value. */
export function pyTruthy(v: PyValue | undefined): boolean {
  if (v === null || v === undefined || v === false || v === "") return false;
  if (v instanceof RawNumber) return Number(v.text) !== 0;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === "object") return Object.keys(v).length > 0;
  return true;
}
