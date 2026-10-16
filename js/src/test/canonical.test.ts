import assert from "node:assert/strict";
import { test } from "node:test";

import { parsePreserving, pythonFloatRepr, pythonJson, pythonJsonCompact, pythonString } from "../canonical.js";
import { hasPython, python } from "./helpers.js";

test("numbers serialise as Python's json.dumps would", () => {
  const cases: Array<[number, string]> = [
    [0, "0"], [1, "1"], [-1, "-1"], [1.5, "1.5"], [-0.5, "-0.5"], [1e16, "1e+16"], [1e15, "1000000000000000"],
    [1e21, "1e+21"], [1e-5, "1e-05"], [0.0001, "0.0001"], [1e-7, "1e-07"], [3.14159, "3.14159"], [1e100, "1e+100"],
    [5e-324, "5e-324"], [1.7976931348623157e308, "1.7976931348623157e+308"], [0.1 + 0.2, "0.30000000000000004"],
    [1e22, "1e+22"], [12345678901234567890, "1.2345678901234567e+19"], [-0, "-0.0"], [123456.789, "123456.789"],
    [2.5e-5, "2.5e-05"], [1234567890123456.7, "1234567890123456.8"],
  ];
  for (const [n, want] of cases) assert.equal(pythonJson(n), want, `pythonJson(${n})`);
  assert.throws(() => pythonJson(NaN), RangeError);
  assert.throws(() => pythonJson(Infinity), RangeError);
});

test("float repr handles the fixed/exponent boundaries like Python", () => {
  assert.equal(pythonFloatRepr(2), "2.0");
  assert.equal(pythonFloatRepr(100), "100.0");
  assert.equal(pythonFloatRepr(1e15), "1000000000000000.0");
  assert.equal(pythonFloatRepr(1e16), "1e+16");
  assert.equal(pythonFloatRepr(0.0001), "0.0001");
  assert.equal(pythonFloatRepr(0.00001), "1e-05");
  assert.equal(pythonFloatRepr(0), "0.0");
});

test("strings escape exactly as ensure_ascii does", () => {
  assert.equal(pythonString('caf\u00e9 \u{1F600} \x01\x7f "q" \\ /'), '"caf\\u00e9 \\ud83d\\ude00 \\u0001\\u007f \\"q\\" \\\\ /"');
  assert.equal(pythonString("\b\t\n\f\r"), '"\\b\\t\\n\\f\\r"');
});

test("objects sort keys by code point and use Python's separators", () => {
  assert.equal(pythonJson({ z: 1, a: [1, 2, { b: null }], t: true }), '{"a": [1, 2, {"b": null}], "t": true, "z": 1}');
  assert.equal(pythonJsonCompact({ b: [1, 2], a: "x" }), '{"a":"x","b":[1,2]}');
  // Astral-plane key sorts after BMP keys, as code points do; UTF-16 order would differ.
  assert.equal(pythonJson({ "\u{1F600}": 1, "\uFFFF": 2 }), '{"\\uffff": 2, "\\ud83d\\ude00": 1}');
  // undefined values are dropped, as JSON.stringify drops them.
  assert.equal(pythonJson({ a: undefined, b: 1 }), '{"b": 1}');
});

test("parsePreserving keeps the numeric lexemes Python would re-emit", () => {
  const text = '{"a": 2.0, "b": 1e5, "c": 1.5e3, "d": 100, "e": -0.0, "f": 0.0, "g": 1E+16, "h": 1000000000000000.0, "i": 123456789012345678901234567890}';
  assert.equal(
    pythonJson(parsePreserving(text)),
    '{"a": 2.0, "b": 100000.0, "c": 1500.0, "d": 100, "e": -0.0, "f": 0.0, "g": 1e+16, "h": 1000000000000000.0, "i": 123456789012345678901234567890}',
  );
  assert.deepEqual(parsePreserving('["a\\u00e9\\n", true, null, []]'), ["a\u00e9\n", true, null, []]);
  assert.throws(() => parsePreserving("{"), SyntaxError);
  assert.throws(() => parsePreserving("[1] x"), SyntaxError);
});

test("differential: random documents canonicalise identically to Python", { skip: !hasPython() && "python3 not available" }, () => {
  const rnd = mulberry32(7);
  const docs: unknown[] = [];
  for (let i = 0; i < 300; i++) docs.push(randomValue(rnd, 0));
  const ours = docs.map((d) => pythonJson(d));
  // Python re-serialises what we wrote; each line must come back unchanged.
  const theirs = python(
    "import json, sys\nfor line in sys.stdin.read().split('\\n'):\n    if line: print(json.dumps(json.loads(line), sort_keys=True))",
    ours.join("\n") + "\n",
  ).trimEnd().split("\n");
  assert.equal(theirs.length, ours.length);
  for (let i = 0; i < ours.length; i++) assert.equal(theirs[i], ours[i], `doc ${i}`);
});

test("differential: Python-written floats round-trip through parsePreserving", { skip: !hasPython() && "python3 not available" }, () => {
  const lines = python(
    "import json, random\nrandom.seed(3)\nfor _ in range(300):\n" +
      "    v = random.choice([random.uniform(-1e20, 1e20), random.random() * 10 ** random.randint(-30, 30), float(random.randint(-10**18, 10**18)), random.randint(-10**25, 10**25), 0.0, -0.0, 1e16, 1e-4])\n" +
      "    print(json.dumps({'v': v, 'l': [v, 2.0, 7]}, sort_keys=True))",
  ).trimEnd().split("\n");
  for (const line of lines) assert.equal(pythonJson(parsePreserving(line)), line);
});

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function randomString(rnd: () => number): string {
  const pool = ["a", "Z", "0", " ", "\n", "\t", '"', "\\", "/", "\u00e9", "\u4e2d", "\u{1F600}", "\x01", "\x7f", "\u2028", "é"];
  let s = "";
  const n = Math.floor(rnd() * 8);
  for (let i = 0; i < n; i++) s += pool[Math.floor(rnd() * pool.length)];
  return s;
}

function randomNumber(rnd: () => number): number {
  const k = rnd();
  if (k < 0.3) return Math.floor(rnd() * 2000) - 1000;
  if (k < 0.5) return (rnd() - 0.5) * 1e6;
  if (k < 0.7) return (rnd() - 0.5) * 10 ** Math.floor(rnd() * 60 - 30);
  if (k < 0.8) return Math.floor(rnd() * 2 ** 53);
  if (k < 0.9) return [0, -0, 1e16, 1e-4, 1e-5, 5e-324, 1.7976931348623157e308][Math.floor(rnd() * 7)]!;
  return rnd();
}

function randomValue(rnd: () => number, depth: number): unknown {
  const k = rnd();
  if (depth > 3 || k < 0.15) return null;
  if (k < 0.3) return rnd() < 0.5;
  if (k < 0.55) return randomNumber(rnd);
  if (k < 0.75) return randomString(rnd);
  if (k < 0.87) {
    const n = Math.floor(rnd() * 4);
    return Array.from({ length: n }, () => randomValue(rnd, depth + 1));
  }
  const n = Math.floor(rnd() * 4);
  const o: Record<string, unknown> = {};
  for (let i = 0; i < n; i++) o[randomString(rnd) || "k"] = randomValue(rnd, depth + 1);
  return o;
}
