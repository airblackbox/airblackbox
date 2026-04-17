# Reply to jagmarques on deepset-ai/haystack#10810

---

@jagmarques Agreed on the distinction between logs and tamper-evident evidence — that's the Article 12 gap most frameworks miss.

For context: I just re-ran the compliance scanner against Haystack's current main branch. **22/22 checks pass, 100% coverage** — including Article 12 record-keeping. Haystack's `structlog` integration, content tracing via `HAYSTACK_CONTENT_TRACING_ENABLED`, and built-in chain verification already satisfy the tamper-evidence requirements that the scanner checks for. @julian-risch and the team addressed this during our earlier exchange on this thread.

For projects that *don't* have that built in (which is most of them), this is a solved problem in the open-source ecosystem. [air-trust](https://pypi.org/project/air-trust/) (Apache 2.0, zero dependencies) provides HMAC-SHA256 tamper-evident audit chains:

```python
import air_trust

# Hooks into Haystack's tracing system
handler = air_trust.trust(pipeline, framework="haystack")
```

Every pipeline step gets signed and chained. Verify independently anytime:

```bash
$ python -m air_trust verify
✓ PASS: Chain is intact (247 records verified)

$ python -m air_trust export --format json > audit_evidence.json
```

No API keys, no server, no paid tiers. Signing happens in-process, chain lives in a local SQLite file. Also ships agent identity binding (Article 14) and policy enforcement as of v0.3.0.

@julian-risch — since the `RISK_ASSESSMENT.md` and `DATA_GOVERNANCE.md` discussion is still open, happy to contribute templates based on the v1.4.0 findings if useful. The corrected checks from your earlier review are still passing cleanly.
