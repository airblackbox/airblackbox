# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **TypeScript package** (`js/`, npm `air-blackbox` 0.1.0, not yet
  published). Records agent actions into the same HMAC chain, Ed25519
  receipts and `.air-evidence` bundles as the Python SDK, byte for byte;
  covenants with the same YAML, precedence and hash; a two-phase `Gate`; RFC
  3161 anchoring on export. Hooks record model calls and tool executions for
  the Vercel AI SDK (5+), the OpenAI Agents SDK (0.17+), LangChain.js /
  LangGraph.js (core 0.3+) and the MCP TypeScript SDK, and with
  `enforce: true` stop a tool the covenant forbids before it runs.
  Differential tests in CI check that the Python SDK verifies this package's
  chains, receipts, bundles and anchors, that this package verifies the
  Python SDK's, and that both can write one chain; a TypeScript bundle also
  passes the browser verifier. Before release it was run as real agents on
  each framework and put through a stress and tamper test, which shaped
  these guarantees: a recording failure never fails the agent's tool call
  (`onRecordError` hears about it); tool arguments, which the model writes,
  cannot satisfy a rule's `unless` or `category`; recorders in one process
  share one chain and a second process is refused rather than forking it;
  an export with missing or unreadable records fails verification; a
  timestamp response must be a granted token over the chain head; and
  covenant YAML is read as PyYAML reads it, so a file has one hash in both
  SDKs.
- **Gateway: Anthropic Messages API.** `POST /v1/messages` is forwarded to
  `ANTHROPIC_URL` (default `https://api.anthropic.com`) with `x-api-key`,
  `anthropic-version` and `anthropic-beta`, streamed or buffered, recorded
  and chained like the OpenAI routes, so one gateway serves both providers.
  On this route the gateway key is read only from `X-Gateway-Key`, never
  from `x-api-key`, which carries the Anthropic credential.
- `eval/competitors/`: a head-to-head of AIR Blackbox 1.17.0 against three
  other open-source EU AI Act scanners (ArkForge, Systima Comply, Asqav) on
  the 144-case parity corpus. Each tool is scored only on the practices it
  claims, with the mapping, caveats and every verdict published. It also
  found two gaps in AIR's own framework detection (LangGraph-only Python, and
  `@openai/guardrails` in TypeScript and JavaScript).

### Changed
- **Covenants: an approval rule whose guard cannot be read now fails
  closed, in both SDKs.** With `permit: issue_refund` beside
  `require_approval: issue_refund` when `amount > 1000`, a missing or
  unreadable amount (`"$5,000"`) used to leave only the permit, so the
  refund went through; it now requires approval. Such a rule only ever
  makes a decision stricter: with no permit, the default forbid stands.
  Decisions change only where a `require_approval` guard is indeterminate.
- **Covenant loading is strict, in both SDKs, with the same messages.**
  Mistakes used to load silently: a misspelled `wehn:` dropped the guard and
  left an unconditional permit, a rule with both `forbid:` and `permit:`
  became a permit, `amount >> 5` and `order.amount > 5` loaded and were
  never true, and a target YAML reads as a number or boolean (`on`, `no`,
  `123`) never matched. Unknown keys, a rule with no action or two, a
  non-string target, `when`, `unless` or `category`, a condition that is
  not `field op value` (or orders against a non-number, or reads a nested
  field), a key repeated in one mapping and unknown top-level keys now raise
  `CovenantError` naming the rule. The four example covenants load
  unchanged, with the same hashes.

### Fixed
- `air-evidence verify` accepted, or crashed on, malformed bundles found by a
  tamper test of TypeScript-written bundles: a manifest repeating a key (the
  signature covers the manifest as parsed, and readers disagree on which
  value counts), bytes before or after the archive (`zipfile` re-bases or
  ignores them), and records nested too deeply to parse (a `RecursionError`
  traceback). Each now fails cleanly at the check concerned, and a bundle
  exported with anchoring turned off shows the recorded reason instead of
  "no anchor recorded". See findings 9-12 in the red-team review.
- Gateway: found by running the provider SDKs (OpenAI and Anthropic, Python
  and TypeScript, plus the Vercel AI SDK and LangChain) through it against
  scripted upstreams:
  - A provider stream that broke partway reached the client as a normal end
    of stream, so SDKs returned a truncated answer as complete, and was
    recorded as a success. The client's connection is now broken too (the
    SDK raises) and the record says `error`, as do an error event inside a
    200 stream and a client that disconnects early.
  - A 120-second overall upstream timeout cut longer streams off silently
    and turned slow non-streamed answers into 502s (which SDKs retry), and
    the server's 180-second write timeout would have cut streams next. Calls
    now end on the caller's own timeout, with limits only on connecting and
    on waiting for a response to start (10 minutes).
  - Only request ids were passed back: `retry-after`, `x-should-retry` and
    the rate-limit headers were dropped, so SDK retries ignored the
    provider's backoff. The provider's response headers now reach the client.
  - Only `Authorization` (and the Anthropic headers) were forwarded, and no
    query string: `OpenAI-Organization` and `OpenAI-Project` were lost (the
    call was billed to the default project), as were `api-version` and the
    Anthropic SDK's `?beta=true`. The client's headers and query string now
    reach the provider, except the gateway's own headers and the gateway key.
  - Concurrent calls opened a new upstream connection almost every time (2
    idle connections per host); the pool now keeps 256.
  - Records of failed calls now say why (HTTP status and the provider's
    error type, never its message), an unreachable upstream returns a JSON
    error the SDKs can parse, and `/v1/messages` calls are recorded as
    provider `anthropic` for aliases and cloud model ids.
- Sandbox: agents using the Anthropic SDK bypassed the sandbox's gateway;
  `ANTHROPIC_BASE_URL` is now set alongside `OPENAI_BASE_URL`.
- README: the gateway section said "everything else in your code stays
  identical", listed Azure and an injection scan the gateway does not have,
  and did not say which endpoints it serves or where each library expects
  the base URL. It now does.
- Gateway recorded zero tokens for every Responses API call, buffered and
  streamed: it only read chat-completions usage names. Usage is now read in
  all three shapes (chat completions, Responses, Anthropic, where cache reads
  and writes count as input).
- Gateway tool filter ignored Responses API tools, which name a tool at the
  top level rather than under `function`, so a blocklisted tool passed
  through unfiltered. Tool extraction and filtering now share one name
  reader, so they cannot disagree about a name again.
- `air-blackbox comply` on a project with no Python now points TypeScript
  and JavaScript at the npm package and gives the Anthropic base URL for the
  gateway.
- `air-blackbox test` failed 5 of 25 on a clean install. Two assertions had
  gone stale: the compliance-engine test expected exactly six groups from a
  report that has carried GDPR and US state-law groups for some time, and the
  HITL test used `Agent(allow_delegation=True)` as its CrewAI fixture, which
  the scanner deliberately stopped counting as human oversight (it is
  agent-to-agent delegation). The fixture is now CrewAI's real idiom,
  `Task(..., human_input=True)`, and the delegation case is asserted NOT to
  count. The three gateway tests are reported as skipped when nothing is
  listening, which is every fresh install, instead of as failures. The
  command now exits 1 on a real failure; it exited 0 regardless before, so it
  could not gate anything.

## [1.17.0] - 2026-10-15

### Added
- Kotlin (`.kt`, `.kts`; Gradle build scripts excluded): shares the Java
  library adapters (LangChain4j, Spring AI, SLF4J, Bean Validation,
  Resilience4j...) and adds its own: Koog and openai-kotlin as model calls,
  runCatching and `.catch {}`, KDoc, kotlin-logging (println excluded),
  Konform and `@field:` constraints, data classes, string-template prompt
  interpolation, Spring AI `entity<T>()`. Top-level functions, expression
  bodies, extension functions and companion objects are counted as
  definitions; constructors and bodiless declarations are not. A Kotlin
  function counts as typed when it has parameters or declares its return
  type (`fun run()` is as untyped as `def run():`).
- `air_blackbox.compliance.snippet.scan_snippet(code, language=None,
  filename=None)`: scan one pasted piece of code through the real scanners,
  as a one-file project. The language is detected from syntax when not
  stated (JSDoc types no longer make JavaScript look like TypeScript), and
  on the parity corpus detection and a stated language give identical
  results for all 642 single-file snippets. This is what the website console
  and the MCP server call instead of carrying their own copies of the checks.
- The compliance scanner reads TypeScript and JavaScript (`.ts`, `.tsx`,
  `.mts`, `.cts`, `.js`, `.jsx`, `.mjs`, `.cjs`) alongside Python, across all
  code checks, GDPR, the US state-law checks and bias. camelCase and
  kebab-case names are matched through a snake_case view, so
  `requireApproval` counts as `require_approval`; try/catch, JSDoc, TS and
  JSDoc types, npm loggers, Zod/Ajv, the Vercel AI SDK and npm guardrail and
  rate-limit packages have their own adapters. Declaration files, minified
  bundles, tool configs, JS build output and JS test conventions
  (`*.test.ts`, `__tests__/`) are handled. Python results are byte-for-byte
  unchanged.
- Java (`.java`): LangChain4j, Spring AI and the official OpenAI/Anthropic
  Java SDKs as model calls; try/catch, Javadoc (prose required), SLF4J/Log4j
  (System.out excluded), Bean Validation and JSON Schema validators,
  Resilience4j/Spring Retry, Bucket4j, Micrometer/OTel tracing, Spring AI
  `.entity()` structured output, Google Cloud DLP. Maven/Gradle output,
  generated sources and JUnit naming (`FooTest`, `FooIT`) are handled.
  Constructors are not counted as methods, like `__init__`. Java is
  statically typed, so its methods always count as typed.
- Jupyter notebooks (`.ipynb`) are read as Python: code cells in order, with
  IPython `%magic` and `!shell` lines commented out, and non-Python kernels
  and `.ipynb_checkpoints` skipped. A notebook gets exactly the result its
  code gets as a `.py` file. Python projects that contain notebooks will see
  them counted from this release on.
- `eval/scanner/parity_corpus.json` and `run_parity.py`: 144 labelled
  programs written in Python, TypeScript, JavaScript, Java and Kotlin, each
  Python one also run as a notebook; every check gives the same status in
  every form (enforced in the test suite). Java and Kotlin cannot express
  untyped parameters, so three type-annotation cases have no version there.
- npm and JVM framework detection (LangChain.js, OpenAI Node SDK, Anthropic
  TypeScript SDK, Vercel AI SDK, OpenAI Agents SDK, Mastra, LlamaIndex.TS,
  Google Gen AI, MCP TypeScript SDK; LangChain4j, Spring AI, OpenAI and
  Anthropic Java SDKs, Google ADK/Gen AI, Azure OpenAI, MCP Java SDK,
  LangGraph4j, Koog, openai-kotlin). Projects with no Python are pointed at the gateway instead
  of a `pip install` trust layer.

### Fixed
- Ordinary AI code was treated as a hiring system, so it got the US hiring
  checks (NYC LL144, California FEHA, Illinois ZIP proxy), often as FAILs.
  `ats` was matched as a suffix ("chats", "formats", "stats") and words like
  "resume" (a stream), "candidate" (reranking, Gemini responses) and
  "screening" were enough on their own. Hiring context now needs at least
  one hiring-specific signal (applicant, recruiting, interview, job title,
  years of experience...) and ignores test fixtures. On this repository's
  own files, `recorder.py` no longer reports a false NYC LL144 failure.
- `air-blackbox comply --scan file.py` crashed with `AttributeError` when
  given a single file. The bias scanner returns a report dict and the engine
  iterated its keys as findings. On directories the same call raised and was
  swallowed, so the Bias and Fairness section never appeared at all. It now
  runs per source file (tests excluded), merges findings by type as warnings,
  and only appears for code that makes decisions about people (the same gate
  as the US hiring checks), because its term lists also match colour names.

## [1.16.0] - 2026-09-26

### Added
- `air_blackbox.record()`: record an agent's actions and export a signed,
  browser-verifiable `.air-evidence` bundle from a plain `pip install`, with
  no server, token or optional extra. Ed25519 by default so the bundle
  verifies at airblackbox.ai/verify; external timestamping on export, with an
  unreachable authority recorded as a gap. Optional `covenant=` records a
  policy decision per action.

### Fixed
- Recruiting-screener covenant: tagging actions no longer fall through to
  default-deny; machine tagging requires an explicit controlled-vocabulary
  assertion. Conditional rules are no longer hidden from the agent (#91).

## [1.15.0] - 2026-08-15

The urgent line: **`pip install "air-blackbox[pqc]"` was broken for anyone who
installed it on 2026-08-15**, the day `pqcrypto` 1.0.0 shipped. This release
fixes it and gathers everything merged since 1.14.0 — the external red-team of
the evidence verifier, the server-to-server ingest path, and a set of honest
corrections to claims that overstated coverage.

**Fixed**
- **Post-quantum signing under `pqcrypto` 1.x.** `pqcrypto` 1.0.0 renamed
  `generate_keypair()` to `keygen()` *and* changed `verify()` to return `None`
  on success and raise on failure. The verifier did `bool(verify(...))`, so a
  **valid** ML-DSA-65 signature read as `False` — every genuine post-quantum
  receipt would have looked tampered. It failed closed (no forgery accepted),
  but the path was unusable. Both API generations are now supported and
  signatures interoperate. Anyone on 1.14.0 with the `pqc` extra should
  upgrade. (#85)
- **The README no longer claims EU AI Act Article 13.** No check ever
  implemented it; the only reference was a demo table. A test now fails the
  build if the documented article set and the implemented one disagree in
  either direction. (#82)
- **US state hiring-law findings are no longer labelled as EU AI Act articles.**
  Illinois HB 3773, NYC LL144 and California FEHA findings were filed under
  `article=16` (EU AI Act provider obligations). They now carry their own
  framework. Separately, every section heading in the exported PDF was
  rendering as a bare "Article " from a wrong dictionary key. (#81)
- **Export no longer times out on the interactive path**, and the ingesting
  tenant can export its own evidence. (#78)

**Security**
- **The evidence verifier was adversarially red-teamed: 75 attacks, 17
  confirmed breaks, all addressed.** Highlights, each with a negative-control
  test: a forged member could be smuggled past the signature via a duplicate
  ZIP entry or a payload disguised as a directory; three compliance counts
  (including `adverse_decisions_missing_reviewer`, the number an auditor reads
  first) were declared but never recomputed; the public transparency-log
  receipt was checked only against a key it carried, never against the log. The
  full write-up, including the limits that remain, is published in
  [docs/security/red-team-2026-08.md](docs/security/red-team-2026-08.md). (#81)

**Added**
- **`air-evidence verify --expect-key <fingerprint>`** pins the expected
  issuer. Unpinned or unanchored bundles now report
  `VERIFIED (UNATTRIBUTED, UNWITNESSED)` rather than a bare pass, and
  `--strict` exits non-zero instead of reporting. `--rekor-verify` fetches the
  transparency-log entry and confirms it matches. (#81)
- **`/ingest`: a server-to-server event intake** for applications that cannot
  own the audit chain themselves. Authenticated, tenant-scoped, single-writer
  by design; returns a signed receipt id per event. See
  [docs/guides/ingest-integration.md](docs/guides/ingest-integration.md).
  (#76, #79)
- **Adverse-decision reviewer gaps are counted separately from engine
  outputs** in the evidence manifest, so a missing human reviewer on a
  rejection is no longer buried inside routine scoring volume. (#80)
- US AI-law references updated to the current statutes — Colorado SB 26-189
  (SB 24-205 was repealed), Illinois HB 3773, California FEHA ADS. (#75)

## [1.14.0] - 2026-08-04

First release since 1.13.2. Everything below was already merged to `main` but
had never been published: a `pip install air-blackbox` was still getting a
build from before the security review, with no anchoring, no evidence
verification, and no `air-blackbox-mcp` / `air-evidence` commands. Releases are
now gated by CI on the built artifact actually importing and running, so the
published package cannot drift silently from the repo again.

**Added**
- **Public transparency-log anchoring (M2).** Exports can publish the chain head
  to Rekor, Sigstore's public append-only log (`AIR_REKOR=1`, opt-in). The new
  `audit_public_log` tool re-derives the bounded chain head against *every*
  entry ever logged under the tenant's anchoring key, so an operator who
  rewrites history **and** re-anchors it is still caught by the older entries —
  closing the documented gap in the RFC 3161 anchor alone. Entries carry the
  full payload inline, so any auditor can interpret them from the public log
  with nothing but the anchoring public key (ADR 0002).
- **ML-DSA-65 (FIPS 204) receipts are now usable.** The signer persists and
  reloads its keypair, so a tenant's post-quantum public key survives a restart;
  previously it regenerated on every construction and silently broke receipt
  continuity. The post-quantum path now runs the full suite in CI. Ed25519
  remains the default. Closes #63.
- **A runnable proof harness** (`python bench/proof/prove.py`): executes five
  real attacks against a plain log, a bare hash chain, and AIR side by side and
  prints a scorecard. CI asserts both that AIR delivers every guarantee and that
  the bare hash chain still *misses* the operator rewrite, so the comparison
  cannot quietly become a rigged demo.
- **"Audit Day" demo** (`demo/hiring_audit_day.py`) plus a 90-second recording
  script — the operator-rewrite catch dramatized on a fictional hiring pipeline,
  running real product code.
- **Cryptographic posture document** (`docs/security/cryptographic-posture.md`):
  the primitives in use, what each is exposed to (including quantum), how the
  system replaces one without a rewrite, and what is not yet production-ready.
- Scheduled auto-export: every tenant with new records gets a fresh signed
  evidence bundle on an interval, without anyone remembering to ask.
- Static dependency discovery for AI-BOM output from requirements.txt,
  pyproject.toml, package.json and package-lock.json, with configurable
  AI-library classification and CycloneDX 1.6 / SPDX 2.3 JSON output for
  `air-blackbox discover`.

**Security**
- Receipt authenticity anchoring (remaining #57 items): `verify_receipt()` accepts an `expected_public_key` so it can reject a receipt signed by an untrusted key (without it, it only proves self-consistency — an attacker can embed their own key); the evidence bundle verifier now requires every receipt to be signed by the **same** key that signed the manifest; and `verify_chain()` reports its `key_source`, with docs making clear the colocated `.air-signing-key` is a zero-config convenience, not a trust anchor against a runs-dir writer (pair with `verify_anchor`).
- Gate covenant conditions now fail **closed**. An ordering comparison on a non-numeric value (e.g. `amount <= 1000` with `amount="1,000,000"`), an unparseable guard, and a `forbid` whose guarded field is missing previously all defaulted to *allow*; they now deny (and a `forbid` with an indeterminate guard stays active). `Gate.walk_delegation_chain` no longer infinite-loops on a cyclic parent link, and `Gate.verify()` surfaces `authorized`/`decision` so a valid signature on a *denied* action isn't mistaken for permission. Fixes #58.
- `air-evidence verify` now checks the external RFC 3161 anchor (new check 6): it re-derives the key-free chain head over the bundle's records and verifies it against the timestamp authority's countersignature, so a rewritten — even perfectly re-signed — history is **detected** by the same command a regulator runs. An unanchored bundle is reported honestly as not rewrite-protected instead of a bare "VERIFIED", and the bundle's stamped chain verdict is now gated (a broken-at-export chain fails). Closes the evidence-bundle part of #57. (Remaining #57 items — `verify_chain`/`verify_receipt` accepting an expected key instead of a co-located/embedded one — are tracked separately.)
- MCP tenant isolation: the authenticated-subject → tenant-directory mapping is now injective (readable prefix + SHA-256 of the full subject). The previous fold-and-truncate mapping could collide two different subjects onto one tenant (e.g. `alice@corp.com` ≡ `alice_corp_com`, or any two subjects sharing a 64-char prefix), and could route an authenticated subject into the shared `_local` root or the `public-demo` chain. Fixes #56.
- MCP JWT auth now **refuses to start** in JWKS mode unless `AIR_MCP_JWT_AUDIENCE` is set (or `AIR_MCP_JWT_ALLOW_ANY_AUDIENCE=1` is explicitly set). Previously, a JWKS-only config accepted any validly-signed token from the IdP, including one minted for a different API behind the same tenant (confused-deputy replay). Static tokens without an explicit subject now derive it from a hash of the full token instead of a 12-char prefix (prefix-sharing tokens no longer collapse onto one tenant), and malformed empty-token entries are skipped. Part of #59.

**Changed**
- `air-blackbox discover --init-registry` now writes `approved-models.json`; `--approved` continues to accept JSON and existing YAML registries.
- MCP OAuth: JWT/JWKS verification mode (`AIR_MCP_JWKS_URL`, `AIR_MCP_JWT_ISSUER`, `AIR_MCP_JWT_AUDIENCE`) — validates IdP-signed tokens locally against published JWKS (WorkOS AuthKit, Auth0, Okta, Keycloak); `pyjwt` added to the `mcp` extra
- Deploy walkthrough for turning on authentication with a DCR-capable IdP so claude.ai custom connectors can log real users in
- README no longer implies the chain is post-quantum secure today; it states Ed25519 now with an ML-DSA-65 upgrade path, and links the posture document.
- Hosted MCP server monitoring: Fly now runs a health check (none was configured before), `/health` write-probes the runs volume so "ok" means "can record evidence" rather than "process is up" (503 otherwise), and optional Sentry error reporting engages only when `SENTRY_DSN` is set — a no-op for self-hosters. New `monitor` extra.
- `mcp` extra pinned to `mcp>=1.0,<2`: mcp 2.0 removed `mcp.server.fastmcp`, which the server imports.

**Fixed**
- `air-blackbox-comply-strict` was broken in every install: the console script pointed at `air_blackbox.precommit:main`, which was never defined, so running it raised `ImportError` immediately. The entry point now exists (and supports `--help`); the hook itself was fine, only its entry point was missing. Releases now resolve every declared console script, not just import its module, so this class of break cannot ship again.
- MCP tenant resolution now fails closed: with auth enabled, a request without an authenticated subject is denied instead of silently recorded into the shared `_local` chain
- Auto-export logs a warning when tenant discovery or a tenant's export state is unreadable (previously silent)
- MCP JWT rejections now log the reason (never the token). A fleet of 401s caused by an audience or issuer mismatch was previously invisible in logs, making a misconfigured deployment undiagnosable.
- `AIR_MCP_RESOURCE_URL` is set explicitly so OAuth discovery reports this server as the protected resource rather than inheriting the IdP's URL, which broke resource-indicator matching for MCP clients.

## [1.6.1] - 2026-03-28

**Fixed**
- Fix standards_map.py STANDARDS_CROSSWALK dict closing prematurely (blocked GDPR/bias imports)
- Fix evidence_bundle.py hash serialization mismatch between manifest and ZIP (sort_keys consistency)

## [1.6.0] - 2026-03-27

**Added**
- Prompt injection detection: 20 weighted patterns across 5 categories
- GDPR scanner: 8 automated checks (consent, minimization, erasure, retention, cross-border, DPIA, processing records, breach notification)
- Bias/fairness scanner: 6 checks (fairness metrics, bias detection, protected attributes, dataset balance, model card, output monitoring)
- ISO 42001 + NIST AI RMF standards crosswalk mapping (8 categories)
- A2A (Agent-to-Agent) compliance protocol with compliance cards, peer verification, signed handshakes
- Evidence bundle exporter: signed ZIP with SHA-256 manifest for auditors
- Feedback loop MVP: user corrections flow into training data for fine-tuned model
- Pre-commit hooks: 4 configurations (basic, strict, GDPR, full)
- Audit chain specification v1.0 (RFC-style document)
- Training data phase 35: injection and GDPR patterns (15 examples)
## [1.5.0] - 2026-03-26

**Added**
- Haystack trust layer
- Claude Agent SDK trust layer
- MCP server registry listing (air-blackbox-mcp v0.1.6)
- Enhanced CLI with verbose compliance output

## [1.4.0] - 2026-03-20

**Added**
- Google ADK trust layer
- Enterprise air-gapped VPS deployment with fine-tuned model
- OTel tracing + dual pipeline
- Deep scan with fine-tuned compliance model

## [1.3.0] - 2026-03-15

**Added**
- MCP server for Claude Desktop and Cursor
- AI-BOM generation (CycloneDX 1.6)
- Shadow AI detection with approved model registry

## [1.2.0] - 2026-03-10

**Added**
- Compliance engine with 20+ checks across 6 EU AI Act articles
- PDF gap analysis reports
- Replay engine with HMAC verification

## [1.1.0] - 2026-03-05

**Added**
- Trust layer framework (LangChain, CrewAI, AutoGen, OpenAI)
- PII detection in prompts
- Non-blocking callback architecture

## [1.0.0] - 2026-03-01

**Added**
- Python SDK (pip install air-blackbox)
- CLI commands: comply, discover, replay, export
- HMAC-SHA256 audit chain
- Gateway client integration

## [0.1.0] - 2026-02-22

**Added**
- Initial release of AIR Blackbox Gateway
- OpenAI-compatible reverse proxy with full request/response capture
- HMAC-SHA256 tamper-evident audit chain
- OpenTelemetry trace emission
- Prompt vault integration with MinIO
- Docker Compose stack
- GitHub Container Registry publishing via CI
