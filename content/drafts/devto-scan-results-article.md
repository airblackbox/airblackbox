# I Scanned 5 Popular Open-Source AI Projects for EU AI Act Compliance. Here's What I Found.

**Tags**: #ai #python #opensource #euaiact

The EU AI Act enforcement deadline is August 2026. Every AI system deployed in the EU will need to meet specific technical requirements around risk management, data governance, documentation, logging, human oversight, and security.

I built an open-source scanner that checks Python AI codebases against these requirements. Then I pointed it at some of the most popular open-source AI projects to see where things stand.

The results were eye-opening.

## What I Scanned

I ran [AIR Blackbox](https://github.com/air-blackbox/gateway) (the scanner itself), [Browser Use](https://github.com/browser-use/browser-use) (79K+ stars), [RAGFlow](https://github.com/infiniflow/ragflow) (76K+ stars), [LiteLLM](https://github.com/BerriAI/litellm) (23K+ stars), and [Superlinked](https://github.com/superlinked/superlinked) (15K+ stars) through the same compliance checks.

Each scan maps code patterns to six articles from the EU AI Act:

- **Article 9** (Risk Management): error handling, fallback patterns, retry logic, risk classification
- **Article 10** (Data Governance): input validation, schema enforcement, PII handling
- **Article 11** (Technical Documentation): docstring coverage, type hints, README, model cards
- **Article 12** (Record-Keeping): structured logging, audit trails, tracing
- **Article 14** (Human Oversight): approval workflows, rate limiting, permission checks
- **Article 15** (Robustness & Security): injection defense, output validation, content filtering

## The Results

| Project | Stars | Score | Art. 9 | Art. 10 | Art. 11 | Art. 12 | Art. 14 | Art. 15 |
|---------|-------|-------|--------|---------|---------|---------|---------|---------|
| AIR Blackbox | 0.1K | **91%** | Pass | Pass | Pass | Pass | Pass | Pass |
| LiteLLM | 23K+ | **48%** | Low | Med | Med | Med | Med | Low |
| Browser Use | 79K+ | **9.4%** | 1.1% | 5.0% | 26.0% | 0.3% | 12.2% | 12.2% |
| RAGFlow | 76K+ | **7.9%** | 1.0% | 7.6% | 30.6% | 0.4% | 4.8% | 3.2% |
| Superlinked | 15K+ | **2.5%** | 0.0% | 3.2% | 8.8% | 0.0% | 0.0% | 3.0% |

To be clear: a low score doesn't mean these are bad projects. Browser Use, RAGFlow, LiteLLM, and Superlinked are excellent tools solving real problems. But they weren't built with EU AI Act technical requirements in mind. Most projects weren't. That's the point.

## What the Gaps Look Like

**Superlinked (2.5%)** is a Python AI search and recommendation framework used by enterprise customers. Zero files passing on risk management, record-keeping, and human oversight. For a framework handling search queries and user data, the complete absence of audit trails is the most striking finding.

**RAGFlow (7.9%)** is a RAG engine processing enterprise documents. It has decent documentation coverage (30.6%), but record-keeping is at 0.4%. Two files out of 500 have structured logging. For a system that ingests documents and generates answers, the EU AI Act specifically requires audit trails showing what went in and what came out.

**Browser Use (9.4%)** is one of the most popular AI browser automation frameworks. It has some human oversight and security patterns already (both at 12.2%), but record-keeping is at 0.3%. One file out of 362 has structured audit logging. For an agent that interacts with live web pages, that's a gap regulators will notice.

**LiteLLM (48%)** scored the highest of the external projects, with solid input validation and existing logging infrastructure. But it still has gaps in risk classification and injection defense. LiteLLM also recently faced a supply chain attack on PyPI and questions about its compliance certifications, which makes verifiable technical compliance even more relevant.

**AIR Blackbox (91%)** was purpose-built for this. It includes HMAC-SHA256 tamper-evident audit chains, drop-in trust layers for 6 frameworks, structured risk assessments, and operator guides. The remaining 9% are runtime infrastructure checks (vault config, OpenTelemetry pipeline, live traffic error rates) that require a production deployment to pass.

## The Pattern

Across all five projects, Article 12 (Record-Keeping) is consistently the weakest. Most Python AI projects don't have structured audit trails. They have `print()` statements and maybe some basic logging, but not the kind of tamper-evident, structured records that Article 12 expects.

Article 11 (Documentation) is consistently the strongest, because good Python projects already have docstrings and type hints. But documentation alone doesn't satisfy the other five articles.

## How the Scanner Works

Install it:

```bash
pip install air-blackbox
```

Scan any Python project:

```bash
air-blackbox comply --scan /path/to/your/project --no-llm --format table
```

That's it. No API keys needed. No cloud calls. Everything runs locally on your machine. ~1,700 installs this month on PyPI.

The scanner walks your Python files and checks for specific patterns. For example, under Article 10 (Data Governance), it looks for Pydantic models, dataclass validators, input sanitization functions, and schema enforcement. Under Article 12 (Record-Keeping), it checks for `import logging`, structured logger usage, and audit trail patterns.

It's a linter for AI governance. It tells you what's missing, not whether you're legally compliant. That's a lawyer's job.

## Try It on Your Own Code

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

The verbose flag shows you exactly which patterns were found (or missing) for each article. You'll get a percentage score and a breakdown of what passed and what didn't.

If you want to start fixing gaps, the trust layers are drop-in:

```python
import air_blackbox

# Attach compliance layers to your framework
air_blackbox.attach("langchain")  # or "crewai", "autogen", "openai", "adk", "rag", "agno"
```

This adds audit logging, input validation, and oversight hooks without changing your application code.

## What This Means for August 2026

Most AI teams haven't started thinking about compliance as a technical problem. It's still seen as a legal/policy concern. But the EU AI Act has specific, measurable technical requirements. You can check for them with code.

The projects I scanned represent 193K+ GitHub stars across the Python AI ecosystem. The average compliance score (excluding AIR Blackbox) is **17%**. The average internal AI project is probably lower.

The good news: these gaps are fixable. Adding structured logging, input validation, and documentation artifacts isn't hard. It's just not something most teams prioritize yet.

Start scanning now. Fix gaps incrementally. Don't wait until July 2026.

## Links

- GitHub: [github.com/air-blackbox](https://github.com/air-blackbox/gateway)
- PyPI: `pip install air-blackbox`
- Live Demo: [airblackbox.ai/demo](https://airblackbox.ai/demo)

Apache 2.0. Stars and PRs welcome.
