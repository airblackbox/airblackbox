/**
 * Canonical JSON, byte-identical to Python's `json.dumps(value, sort_keys=True)`.
 *
 * The chain hash, the covenant hash and the receipt signatures are all computed
 * over this form, and the Python SDK's verifier recomputes them by re-serialising
 * the parsed record. So a record written here verifies there only if every byte
 * matches: sorted keys, `", "` and `": "` separators, `ensure_ascii` escaping
 * (non-ASCII as lowercase `\uXXXX`, astral code points as surrogate pairs, DEL
 * escaped too), and Python's float repr for non-integral numbers.
 *
 * Numbers: a JavaScript number has no int/float distinction, Python does. Every
 * integral number below 1e16 is written as an integer, which Python reads back
 * as an int and re-serialises identically. Anything else uses Python's float
 * repr rules (shortest round-trip digits, exponent form outside 1e-4..1e16), so
 * `1e21` is written `1e+21` and Python's float repr of the parsed value agrees.
 *
 * Verifying files written by Python needs the opposite direction: `2.0` in a
 * file must stay `2.0`, which JSON.parse cannot do. `parsePreserving` keeps the
 * original numeric lexeme for that case.
 */

/** A number whose source text is preserved through parse and re-serialise. */
export class RawNumber {
  constructor(public readonly text: string) {}
  valueOf(): number {
    return Number(this.text);
  }
  /** For JSON.stringify of informational documents; the canonical form uses `text`. */
  toJSON(): number {
    return Number(this.text);
  }
}

export type Canonical =
  | null
  | boolean
  | number
  | string
  | RawNumber
  | Canonical[]
  | { [key: string]: Canonical };

/** Serialise like Python's json.dumps(value, sort_keys=True). */
export function pythonJson(value: unknown): string {
  const out: string[] = [];
  writeValue(out, value);
  return out.join("");
}

/** The canonical bytes, as the hashes and signatures consume them. */
export function pythonJsonBytes(value: unknown): Buffer {
  return Buffer.from(pythonJson(value), "utf8");
}

/** Like pythonJson but with Python's `separators=(",", ":")` (no spaces). */
export function pythonJsonCompact(value: unknown): string {
  const out: string[] = [];
  writeValue(out, value, true);
  return out.join("");
}

/**
 * Indented, for files people read. Every scalar is written exactly as the
 * canonical form writes it, so a reader that parses the file and
 * re-serialises canonically gets the bytes that were hashed. (JSON.stringify
 * would not: it writes 2**60 as integer digits, the canonical form as a
 * float, and the chain would no longer verify.)
 */
export function pythonJsonPretty(value: unknown, indent = 2): string {
  return pretty(value, 0, " ".repeat(indent));
}

function pretty(v: unknown, depth: number, pad: string): string {
  const inner = pad.repeat(depth + 1);
  const outer = pad.repeat(depth);
  if (Array.isArray(v)) {
    if (v.length === 0) return "[]";
    return "[\n" + v.map((x) => inner + pretty(x, depth + 1, pad)).join(",\n") + "\n" + outer + "]";
  }
  if (v && typeof v === "object" && !(v instanceof RawNumber) && !(v instanceof Date)) {
    const obj = v as Record<string, unknown>;
    const keys = Object.keys(obj).filter((k) => obj[k] !== undefined).sort(compareCodePoints);
    if (keys.length === 0) return "{}";
    return "{\n" + keys.map((k) => inner + pythonString(k) + ": " + pretty(obj[k], depth + 1, pad)).join(",\n") + "\n" + outer + "}";
  }
  return pythonJson(v);
}

function writeValue(out: string[], v: unknown, compact = false): void {
  if (v === null || v === undefined) {
    out.push("null");
    return;
  }
  if (v instanceof RawNumber) {
    out.push(v.text);
    return;
  }
  switch (typeof v) {
    case "boolean":
      out.push(v ? "true" : "false");
      return;
    case "number":
      out.push(pythonNumber(v));
      return;
    case "bigint":
      out.push(v.toString());
      return;
    case "string":
      out.push(pythonString(v));
      return;
    case "object":
      break;
    default:
      // functions, symbols: Python's json would refuse too.
      throw new TypeError(`cannot canonicalise a ${typeof v}`);
  }
  if (Array.isArray(v)) {
    out.push("[");
    v.forEach((item, i) => {
      if (i) out.push(compact ? "," : ", ");
      writeValue(out, item, compact);
    });
    out.push("]");
    return;
  }
  if (v instanceof Date) {
    out.push(pythonString(v.toISOString()));
    return;
  }
  const obj = v as Record<string, unknown>;
  // Python sorts keys by code point; JS default sort compares UTF-16 code
  // units, which differs only for astral characters. Compare by code point.
  const keys = Object.keys(obj)
    .filter((k) => obj[k] !== undefined)
    .sort(compareCodePoints);
  out.push("{");
  keys.forEach((k, i) => {
    if (i) out.push(compact ? "," : ", ");
    out.push(pythonString(k), compact ? ":" : ": ");
    writeValue(out, obj[k], compact);
  });
  out.push("}");
}

function compareCodePoints(a: string, b: string): number {
  const ia = a[Symbol.iterator]();
  const ib = b[Symbol.iterator]();
  for (;;) {
    const na = ia.next();
    const nb = ib.next();
    if (na.done && nb.done) return 0;
    if (na.done) return -1;
    if (nb.done) return 1;
    const ca = na.value.codePointAt(0)!;
    const cb = nb.value.codePointAt(0)!;
    if (ca !== cb) return ca - cb;
  }
}

/** Python's json string encoding with ensure_ascii=True. */
export function pythonString(s: string): string {
  let r = '"';
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    switch (c) {
      case 0x22: r += '\\"'; break;
      case 0x5c: r += "\\\\"; break;
      case 0x08: r += "\\b"; break;
      case 0x09: r += "\\t"; break;
      case 0x0a: r += "\\n"; break;
      case 0x0c: r += "\\f"; break;
      case 0x0d: r += "\\r"; break;
      default:
        if (c >= 0x20 && c < 0x7f) {
          r += s[i];
        } else {
          // Python emits one \uXXXX per UTF-16 code unit, so a lone or paired
          // surrogate is written as-is; that is exactly what charCodeAt yields.
          r += "\\u" + c.toString(16).padStart(4, "0");
        }
    }
  }
  return r + '"';
}

/** Python's repr for a number, as json.dumps writes it. */
export function pythonNumber(n: number): string {
  if (!Number.isFinite(n)) {
    // Python would write NaN/Infinity, which is not JSON and which the Go
    // gateway rejects. Refuse rather than write a record nothing can verify.
    throw new RangeError(`non-finite number ${n} cannot be recorded`);
  }
  if (Object.is(n, -0)) return "-0.0";
  if (Number.isInteger(n) && Math.abs(n) < 1e16) return n.toFixed(0);
  return pythonFloatRepr(n);
}

/**
 * Python's float.__repr__: shortest round-trip digits (which JS also
 * produces), laid out with Python's thresholds: fixed notation when
 * 1e-4 <= |x| < 1e16, otherwise `d.ddde[+-]XX` with at least two exponent
 * digits. A fixed-notation integral value keeps a trailing `.0`.
 */
export function pythonFloatRepr(n: number): string {
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  // toExponential() with no argument gives the shortest round-trip digits.
  const exp = abs.toExponential();
  const m = /^(\d)(?:\.(\d+))?e([+-]\d+)$/.exec(exp);
  if (!m) throw new RangeError(`unexpected float form ${exp}`);
  const digits = m[1]! + (m[2] ?? "");
  const e = parseInt(m[3]!, 10);
  if (e >= -4 && e < 16) {
    let s: string;
    if (e >= 0) {
      if (digits.length <= e + 1) {
        s = digits + "0".repeat(e + 1 - digits.length) + ".0";
      } else {
        s = digits.slice(0, e + 1) + "." + digits.slice(e + 1);
      }
    } else {
      s = "0." + "0".repeat(-e - 1) + digits;
    }
    return sign + s;
  }
  const mant = digits.length > 1 ? digits[0] + "." + digits.slice(1) : digits;
  const expStr = (e < 0 ? "-" : "+") + String(Math.abs(e)).padStart(2, "0");
  return sign + mant + "e" + expStr;
}

/**
 * Parse JSON keeping each number's source text (as a RawNumber), so a value
 * written by another implementation re-serialises byte-for-byte. Object key
 * order is irrelevant (keys are sorted on output); duplicate keys keep the
 * last value, as Python's json.loads does.
 */
export function parsePreserving(text: string): Canonical {
  let i = 0;
  const err = (msg: string): never => {
    throw new SyntaxError(`${msg} at offset ${i}`);
  };
  const ws = (): void => {
    while (i < text.length && " \t\n\r".includes(text[i]!)) i++;
  };
  const value = (): Canonical => {
    ws();
    const c = text[i];
    if (c === "{") {
      i++;
      const obj: { [k: string]: Canonical } = {};
      ws();
      if (text[i] === "}") { i++; return obj; }
      for (;;) {
        ws();
        if (text[i] !== '"') err("expected string key");
        const k = str();
        ws();
        if (text[i] !== ":") err("expected ':'");
        i++;
        // defineProperty, not assignment: `obj["__proto__"] = v` would set
        // the prototype and drop the key, so the record would no longer
        // re-serialise to the bytes it was hashed as.
        Object.defineProperty(obj, k, { value: value(), enumerable: true, writable: true, configurable: true });
        ws();
        if (text[i] === ",") { i++; continue; }
        if (text[i] === "}") { i++; return obj; }
        err("expected ',' or '}'");
      }
    }
    if (c === "[") {
      i++;
      const arr: Canonical[] = [];
      ws();
      if (text[i] === "]") { i++; return arr; }
      for (;;) {
        arr.push(value());
        ws();
        if (text[i] === ",") { i++; continue; }
        if (text[i] === "]") { i++; return arr; }
        err("expected ',' or ']'");
      }
    }
    if (c === '"') return str();
    if (text.startsWith("true", i)) { i += 4; return true; }
    if (text.startsWith("false", i)) { i += 5; return false; }
    if (text.startsWith("null", i)) { i += 4; return null; }
    // Python's json.dumps writes these for non-finite floats (allow_nan is
    // its default), so a Python-written record can carry them.
    for (const token of ["NaN", "Infinity", "-Infinity"]) {
      if (text.startsWith(token, i)) { i += token.length; return new RawNumber(token); }
    }
    const m = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text.slice(i));
    if (!m || !m[0]) return err("unexpected token");
    i += m[0].length;
    return new RawNumber(pythonNumberLexeme(m[0]));
  };
  const str = (): string => {
    i++; // opening quote
    let s = "";
    for (;;) {
      if (i >= text.length) err("unterminated string");
      const c = text[i]!;
      if (c === '"') { i++; return s; }
      if (c === "\\") {
        const n = text[i + 1];
        i += 2;
        switch (n) {
          case '"': s += '"'; break;
          case "\\": s += "\\"; break;
          case "/": s += "/"; break;
          case "b": s += "\b"; break;
          case "f": s += "\f"; break;
          case "n": s += "\n"; break;
          case "r": s += "\r"; break;
          case "t": s += "\t"; break;
          case "u": {
            const hex = text.slice(i, i + 4);
            if (!/^[0-9a-fA-F]{4}$/.test(hex)) err("bad \\u escape");
            s += String.fromCharCode(parseInt(hex, 16));
            i += 4;
            break;
          }
          default:
            err("bad escape");
        }
        continue;
      }
      s += c;
      i++;
    }
  };
  const v = value();
  ws();
  if (i !== text.length) err("trailing data");
  return v;
}

/**
 * How Python re-serialises a numeric lexeme it parsed: integers (no '.', no
 * exponent) verbatim; anything else through float repr.
 */
function pythonNumberLexeme(lexeme: string): string {
  if (!/[.eE]/.test(lexeme)) return lexeme;
  return pythonNumber(Number(lexeme)) === lexeme ? lexeme : pythonFloatRepr(Number(lexeme));
}
