# Upstreaming Plan: OTel Collector Contrib Processor

Goal: get an AIR-style GenAI redaction/audit processor accepted into
`opentelemetry-collector-contrib`. If it ships in the standard collector
distribution, every platform team can enable AIR semantics with a config
change. This is distribution through the standard, and it compounds unlike
any marketing channel.

This is the slow-burn track. Expect months, not weeks. Work it in parallel
with everything else.

## What we propose

A vendor-neutral processor, working name `genaiaudit`, that:

1. Redacts or hash-and-previews GenAI content attributes on spans
   (prompt/completion bodies) before export, configurable per attribute
2. Optionally vaults original content to an S3-compatible store and replaces
   it with a reference, so trace backends never hold sensitive content
3. Emits content checksums so downstream evidence remains verifiable

Critical framing: the proposal must be vendor-neutral. It is "a privacy and
integrity processor for GenAI telemetry," not "the AIR Blackbox processor."
The AIR brand benefits from being the reference implementation and the
maintainer, not from naming rights.

## Prerequisites (do these first)

- [x] Gateway emits current GenAI semconv attributes (see docs/SEMCONV.md)
- [ ] Existing collector processor code cleaned to contrib code structure
      (factory.go, config.go with validation, processor.go, README, tests
      with >80% coverage, testdata configs)
- [ ] Benchmarks published (BENCHMARKS.md) - reviewers check whether the
      author runs this in production-like conditions
- [ ] Lint passes with the contrib repo's golangci-lint config

## The process (verify current details in contrib CONTRIBUTING.md)

1. **Open a "New component proposal" issue** in
   opentelemetry-collector-contrib using their issue template. State the
   problem (sensitive GenAI content leaking into trace backends), the
   proposed config surface, and why existing processors (redaction,
   transform) do not cover it. That last argument is the one that decides
   acceptance: the existing `redaction` processor works on attribute
   allowlists, not GenAI-aware content handling with vault-and-reference.
2. **Find a sponsor.** New contrib components require a sponsor from the
   project approvers/maintainers. Engage in the #otel-collector and GenAI
   SIG channels on the CNCF Slack before and after filing. The GenAI
   observability SIG is the right audience; attend a SIG call and present
   the proposal in two minutes.
3. **Ship in stages.** Contrib expects new components to enter as alpha
   with a vendor (you) listed as code owner. First PR is skeleton + config,
   then functionality. Small PRs get reviewed; big ones rot.
4. **Maintain it.** Code ownership is the moat. The maintainer of the
   standard GenAI audit processor has a permanent seat in every
   conversation about AI telemetry governance.

## Fallback if contrib declines

Distribute the processor as a standalone OCB (OpenTelemetry Collector
Builder) module. Teams add one line to their builder manifest. Less
distribution than contrib, still standards-native, zero gatekeepers. The
proposal effort is not wasted either way: the SIG conversations are the
relationship channel for the GenAI semconv work itself.

## Timeline expectation

- Weeks 1-2: code restructure to contrib layout, tests, lint
- Week 3: proposal issue + SIG presentation
- Weeks 4-12: sponsor search, review cycles
- Realistic landing: 3-6 months from proposal

Note: process details (sponsor requirements, issue templates, code
structure) evolve. Before filing, re-read
https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/CONTRIBUTING.md
