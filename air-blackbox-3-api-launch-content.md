# AIR Blackbox 3-API Launch Content Pack

---

## 1. HACKER NEWS POST

**Title:**
Show HN: Three open-source APIs for AI governance -- detect shadow AI, enforce policies, scan for EU AI Act compliance

**URL:** https://airblackbox.ai/shadow-ai

**First comment (post immediately after submitting):**

Hey HN, I'm Jason. I built AIR Blackbox, an open-source EU AI Act compliance tool. Today I'm shipping three APIs that share one key and one credit balance:

**API 1: Shadow AI Detection** (`POST /api/detect`)
Paste any professional text, get a confidence score for AI-generated content. Context-aware across 8 industries (hiring, legal, finance, healthcare, insurance, customer support, education, general). Maps findings to actual regulations -- ABA Model Rules, EEOC guidance, EU AI Act Art. 50, etc.

**API 2: Policy Verification** (`POST /api/policy`)
Send an AI action (tool call, model name, provider, framework) and get back approve/deny/flag with the matching rule. Ships with a default policy covering provider allowlists, deprecated model blocklists, high-risk action detection (delete_user, send_payment, deploy_production), PII pattern matching, and framework checks. Pass your own policy object to customize.

**API 3: Compliance Scan** (`POST /api/scan`)
Send Python code, get an EU AI Act compliance score (0-100) with findings mapped to Articles 9, 10, 11, 12, 14, and 15. Checks for error handling, PII redaction, logging, tracing, audit trails, human oversight, injection defense, and output validation. Also checks US hiring laws (Illinois HB 3773, NYC LL144, California FEHA) when hiring context is detected.

All three work without an API key (25 free calls/month). Prepaid credits at $0.015-$0.03/call if you need more.

The scan engine is pattern-based static analysis -- no LLM in the loop for the API itself, so results are deterministic and fast (<5ms). I'm separately fine-tuning a local Llama 3.2 1B model for deeper analysis that runs entirely on-device.

Happy to answer questions about the architecture, the EU AI Act technical requirements, or why I think policy-as-code for AI agents is going to be a big deal.

GitHub: https://github.com/air-blackbox
Try it: https://airblackbox.ai/shadow-ai

---

## 2. LINKEDIN POST

The EU AI Act high-risk deadline is 3 months away.

Most companies I talk to have the same answer when I ask about their AI governance: "We're working on it."

Working on it isn't a compliance strategy. So I built three APIs that give teams something concrete to ship today.

One API key. One credit balance. Three capabilities:

Detect -- paste any professional text, find out if AI wrote it. Context-aware across hiring, legal, finance, healthcare, and four more industries. Maps to actual regulations, not generic warnings.

Policy -- send an AI agent's action before it executes. Get back approve, deny, or flag-for-human-review. Default rules catch dangerous operations like delete_user, send_payment, deploy_production. Bring your own policy for custom rules.

Scan -- send Python AI code, get a compliance score against EU AI Act Articles 9 through 15. Checks error handling, PII, audit trails, human oversight, injection defense. Also catches US hiring AI violations (Illinois, NYC, California).

25 free calls/month. No key needed. Takes 10 seconds to test.

The pattern I keep seeing: companies spend $100K+ on governance platforms when what they actually need is a linter they can drop into CI/CD. That's what this is.

25 free calls/month. No key needed. Link in comments.

#AIGovernance #EUAIAct #OpenSource #Python #AICompliance

**FIRST COMMENT (post immediately after):**

Try all 3 APIs here: https://airblackbox.ai/shadow-ai

Open source: https://github.com/air-blackbox

---

## 3. DEV.TO ARTICLE

**Title:** I Built 3 APIs to Solve AI Governance -- Here's How They Work

**Tags:** #ai #python #opensource #euaiact

---

Every company using AI agents in production has the same three blind spots:

1. People on your team are using AI to write professional content, and nobody knows.
2. Your AI agents can execute dangerous actions with zero policy checks.
3. Your Python AI code doesn't meet EU AI Act technical requirements, and the deadline is August 2026.

I built an API for each one. They share a single API key and credit balance. Here's how they work.

### API 1: Shadow AI Detection

The problem: a recruiter writes candidate evaluations using ChatGPT. A lawyer drafts memos with Claude. A claims adjuster generates assessments with GPT-4. Nobody told compliance.

The API takes any text and returns a confidence score with detection signals:

```bash
curl -X POST https://airblackbox.ai/api/detect \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The candidate demonstrates strong analytical capabilities and exhibits excellent communication skills across multiple domains.",
    "context": "hiring"
  }'
```

Response:

```json
{
  "score": 0.78,
  "verdict": "likely_ai",
  "signals": [
    {"name": "Vocabulary uniformity", "score": 0.82, "detail": "Low lexical variance..."},
    {"name": "Hedge density", "score": 0.71, "detail": "Excessive qualifying language..."}
  ],
  "regulatory_exposure": [
    {"law": "EEOC Guidance on AI in Hiring", "risk": "AI-generated evaluations may mask bias..."},
    {"law": "EU AI Act Art. 50", "risk": "Transparency obligation for AI-generated content..."}
  ]
}
```

The `context` parameter is the key differentiator. Set it to `hiring`, `legal`, `finance`, `healthcare`, `insurance`, `customer_support`, `education`, or `general`. Each context loads industry-specific detection signals and maps findings to the actual regulations that apply.

### API 2: Policy Verification

The problem: your LangChain agent can call `delete_user`, `send_payment`, or `deploy_production` with no guardrails. You need policy-as-code for AI actions.

```bash
curl -X POST https://airblackbox.ai/api/policy \
  -H "Content-Type: application/json" \
  -d '{
    "action": "delete_user",
    "model": "gpt-4o",
    "provider": "openai",
    "framework": "langchain"
  }'
```

Response:

```json
{
  "decision": "flag",
  "reason": "Action 'delete_user' is blocked by policy",
  "risk_level": "critical",
  "matched_rules": [{
    "rule_id": "high-risk-actions",
    "description": "Flag dangerous tool actions for human review",
    "decision": "flag",
    "risk_level": "critical"
  }]
}
```

The default policy includes five rule types:

- **Provider allowlist** -- only approved AI providers (OpenAI, Anthropic, Google, Azure, AWS Bedrock)
- **Model blocklist** -- blocks deprecated models (GPT-3.5 variants, text-davinci, code-davinci)
- **Action blocklist** -- flags dangerous operations (delete, payment, deploy, permission changes)
- **PII pattern matching** -- catches actions that might expose personal data (export_user, download_customer, send_email_bulk)
- **Framework allowlist** -- flags unrecognized agent frameworks

You can pass your own policy object to customize every rule. The engine returns approve, deny, or flag with the specific rule that matched.

### API 3: Compliance Scan

The problem: your Python AI code needs to pass EU AI Act technical requirements by August 2026, and you have no idea where the gaps are.

```bash
curl -X POST https://airblackbox.ai/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "code": "from openai import OpenAI\nclient = OpenAI()\nresult = client.chat.completions.create(\n    model=\"gpt-4o\",\n    messages=[{\"role\": \"user\", \"content\": \"hello\"}]\n)"
  }'
```

Response (trimmed):

```json
{
  "score": 15,
  "articles": [
    {"number": 9, "title": "Risk Management", "score": 33},
    {"number": 10, "title": "Data Governance", "score": 25},
    {"number": 12, "title": "Record-Keeping", "score": 0},
    {"number": 14, "title": "Human Oversight", "score": 0},
    {"number": 15, "title": "Robustness", "score": 25}
  ],
  "findings": [
    {
      "name": "LLM call error handling",
      "article": 9,
      "status": "fail",
      "severity": "high",
      "meaning": "Your code calls an LLM API without any error handling...",
      "fix": "Wrap your LLM calls in try/except blocks...",
      "time_estimate": "15 minutes"
    }
  ]
}
```

Every finding includes a plain-English explanation of what's wrong, how to fix it, and how long the fix takes. The scan covers:

- **Article 9** -- Error handling, retry logic, rate limiting
- **Article 10** -- PII handling, input validation
- **Article 11** -- Docstrings, type hints
- **Article 12** -- Logging, tracing, audit trails
- **Article 14** -- Human-in-the-loop mechanisms
- **Article 15** -- Injection defense, output validation

When hiring-related code is detected, it also checks US laws: Illinois HB 3773 (ZIP code as proxy), NYC Local Law 144 (bias audits), and California FEHA (4-year data retention).

### How the Credit System Works

All three APIs share one key and one credit balance:

1. **Free tier**: 25 calls/month across all APIs. No key needed.
2. **Prepaid credits**: Buy packs of 500 ($15), 2,000 ($50), or 10,000 ($150). Credits never expire. Use them on any API.

Generate a key:

```bash
curl -X POST https://airblackbox.ai/api/keys \
  -H "Content-Type: application/json" \
  -d '{"email": "you@company.com"}'
```

Then pass it as a Bearer token on any API call.

### Architecture Notes

The scan engine is deterministic pattern-based static analysis. No LLM in the loop, so results are reproducible and fast (under 5ms). The policy engine evaluates rules sequentially with escalation logic (deny > flag > approve) and tracks the highest risk level across all matched rules.

I'm separately fine-tuning a Llama 3.2 1B model on compliance analysis that will run entirely on-device for deeper scanning. That's the local-first moat: your code never has to leave your machine.

### Try It

- **Dashboard & docs**: [airblackbox.ai/shadow-ai](https://airblackbox.ai/shadow-ai)
- **GitHub**: [github.com/air-blackbox](https://github.com/air-blackbox)
- **CLI scanner**: `pip install air-compliance-checker && air-compliance scan .`

The whole project is open source under Apache 2.0. Star it, try it, break it.

---

## 4. TWITTER POST

**Tweet text:**

Shipped 3 APIs today for AI governance:

1. Detect shadow AI in any professional text
2. Policy-check AI agent actions before they execute
3. Scan Python code for EU AI Act compliance

One key. One credit balance. 25 free calls/month.

Try it: airblackbox.ai/shadow-ai

**Image prompt (for AI image generation or manual creation):**

See the attached SVG below -- use it as the Twitter card image.

---
