/**
 * Test helpers. Differential checks run against Python when it is available:
 * stdlib-only checks need any python3; SDK checks need `air_blackbox`
 * importable (set AIR_PYTHON to an interpreter and PYTHONPATH to the sdk
 * directory, as CI does). Missing Python skips those checks with a note, it
 * does not fail the suite.
 */
import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

export function tmpdir(prefix = "air-js-"): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

const PYTHON = process.env["AIR_PYTHON"] ?? "python3";

let pythonOk: boolean | undefined;
let sdkOk: boolean | undefined;

export function hasPython(): boolean {
  if (pythonOk === undefined) {
    const r = spawnSync(PYTHON, ["-c", "import json, hmac, hashlib"], { encoding: "utf8" });
    pythonOk = r.status === 0;
  }
  return required(pythonOk, "python");
}

/**
 * In CI the differential tests are the point of the suite, so a missing
 * Python must fail loudly rather than skip quietly: set AIR_REQUIRE_PYTHON=1.
 */
function required(ok: boolean, what: string): boolean {
  if (!ok && process.env["AIR_REQUIRE_PYTHON"]) {
    throw new Error(`AIR_REQUIRE_PYTHON is set but ${what} is not available via ${PYTHON}`);
  }
  return ok;
}

export function hasAirSdk(): boolean {
  if (sdkOk === undefined) {
    // Import the Ed25519 primitives, not just the package: a cryptography
    // install with a broken native backend imports at the top level and
    // then fails on first use.
    const r = spawnSync(PYTHON, ["-c", "import air_blackbox, yaml\nfrom cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey\nEd25519PrivateKey.generate()"], { encoding: "utf8" });
    sdkOk = r.status === 0;
  }
  return required(sdkOk, "the air_blackbox SDK (with working Ed25519)");
}

/** Run a Python script with stdin; returns stdout, throws on non-zero exit. */
export function python(script: string, stdin = ""): string {
  const r = spawnSync(PYTHON, ["-c", script], { input: stdin, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  if (r.status !== 0) throw new Error(`python failed (${r.status}): ${r.stderr}`);
  return r.stdout;
}

export function readJson(file: string): unknown {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
