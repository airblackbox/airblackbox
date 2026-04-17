# Reply to jagmarques on deepchecks/deepchecks#2813

---

Good callout on Article 12 — tamper-evident record-keeping is a separate requirement from validation.

I ran the latest version of the compliance scanner against Deepchecks' current main branch. It scores **91% — 18 pass, 2 warn, 2 fail** across 22 checks. The Article 12 audit trail check is one of the two failures — confirming the gap you're flagging:

| Article | Status | Notes |
|---------|--------|-------|
| Art. 9 — Risk Management | ⚠️ WARN | Risk audit logging not detected |
| Art. 10 — Data Governance | ❌ FAIL | No Pydantic/schema input validation found |
| Art. 11 — Technical Docs | ✅ PASS | 2,181 docstrings, 71 doc files |
| Art. 12 — Record-Keeping | ❌ FAIL | **No dedicated audit trail for AI decisions** |
| Art. 14 — Human Oversight | ⚠️ WARN | No human review flow detected |
| Art. 15 — Security | ✅ PASS | 163 test files, input sanitization present |

For the Article 12 gap specifically, this is a solved problem in the open-source ecosystem. [air-trust](https://pypi.org/project/air-trust/) (Apache 2.0, zero dependencies) provides HMAC-SHA256 tamper-evident audit chains:

```python
import air_trust
client = air_trust.trust(your_llm_client)
# Every call is now signed and chained
```

Verify independently:
```bash
$ python -m air_trust verify
✓ PASS: Chain is intact
```

No API keys, no server, no paid tiers — signing happens in-process, chain lives in a local SQLite file. Also ships agent identity (Article 14) and policy enforcement as of v0.3.0.

Agreed that treating validation (Deepchecks) and record-keeping (HMAC audit chain) as complementary layers is the right architecture. Anyone can try the scanner themselves at [airblackbox.ai/scan](https://airblackbox.ai/scan) — no install required.
