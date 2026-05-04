# Email to flair (Humboldt-Universität zu Berlin)

**To**: alan.akbik@informatik.hu-berlin.de
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for flair (140 files scanned)

---

Hey Alan,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran flairNLP/flair through the scanner and wanted to share what I found. flair is in an unusual position for a research-led NLP library: it shipped originally out of Zalando Research, it's now developed at the HU Berlin ML chair, and it underpins production NER, PoS tagging, and biomedical text pipelines at a long list of EU enterprises. That makes the library itself, and the conventions it normalizes, a meaningful upstream input into the Article 9-15 evidence those enterprises are going to have to produce by August 2026 - a German maintainer of the canonical European NLP framework is exactly the kind of project that gets cited in customer conformity assessments.

**Summary**: 140 Python files scanned, 16/58 checks passing (28%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/11 passing |

The good news first: Article 12 at 4/9 is unusually strong for a pre-LLM-era NLP library. Trainer logging, model loading provenance, and the way checkpoint metadata is preserved are all visible to static analysis and map cleanly to "audit trails" in the EU AI Act sense. GDPR retention/processing patterns also showed up, which is rare for a library this small.

The standout gap is Article 14 at 0/9. flair's tagger and classifier components return predictions and confidence scores, but there is no first-class oversight primitive baked into the public API - no built-in confidence-threshold gate, no abstain/escalate hook on `Sentence.predict`, no documented "review queue" pattern for predictions a human is meant to confirm before they reach a downstream system. For a library used in legal, clinical, and public-sector NER (all Annex III high-risk territory in the EU AI Act), a small `flair.oversight` namespace - a `predict_with_review(threshold, on_uncertain=...)` API and a docs section that maps it to Article 14 - would move that 0/9 toward 5/9 and let every flair-using compliance team point at one canonical pattern. The same exercise on Article 10 (a documented model-card / data-card schema for `TextClassifier` and `SequenceTagger`) closes most of the data-governance gap.

**To be clear**: this doesn't mean flair is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given how many EU teams pin flair as the NLP layer underneath their Annex III workloads, even a short "AI Act notes" chapter in the docs (covering the existing Article 12 strengths, the model-card schema, and the recommended Article 14 oversight pattern) would save thousands of downstream teams from answering the same audit questionnaire cold. Happy to share the full scan output, or to chat about what a `flair.compliance` module could look like, if any of this is useful for the roadmap.

Best,
Jason Shotwell
https://airblackbox.ai
