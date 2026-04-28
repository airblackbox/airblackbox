# Shadow AI Detection Module -- Product Requirements Document

**Author:** Jason Shotwell
**Date:** April 28, 2026
**Status:** Draft
**Version:** 0.1

---

## Problem Statement

Recruiters and hiring managers are pasting resumes, candidate notes, and evaluation criteria into ChatGPT, Claude, Gemini, and other LLMs to generate screening decisions -- with zero audit trail, no bias controls, and no compliance documentation. This "shadow AI" usage happens outside sanctioned tools and leaves organizations exposed to regulatory liability under NYC LL144, Illinois HB 3773, California FEHA, Colorado CAIA, and EU AI Act Annex III (high-risk hiring classification).

No existing compliance tool detects this. Every competitor focuses on scanning code or auditing deployed models. Nobody is scanning for humans using AI informally in hiring workflows.

---

## Success Metrics

- 5 enterprise design partners running pilots within 90 days of MVP launch
- 50 organizations on waitlist before first line of code ships (validated demand)
- $10K MRR within 6 months of GA launch
- Detection accuracy: 85%+ precision on AI-generated evaluation language, less than 10% false positive rate

---

## User Stories

As an **HR Compliance Officer**, I want to know which recruiters on my team are using unsanctioned AI tools to evaluate candidates so that I can ensure we meet NYC LL144 and Illinois HB 3773 requirements before an audit.

As a **Chief People Officer**, I want a dashboard showing shadow AI usage patterns across my recruiting team so that I can make informed decisions about which AI tools to formally adopt and govern.

As a **Recruiter**, I want clear guidance on which AI tools are approved and which are not so that I can use AI to be more productive without putting the company at legal risk.

As a **Legal/GRC Analyst**, I want evidence that our hiring process has controls against unsanctioned AI usage so that I can include this in our compliance documentation.

---

## Market Sizing

**TAM (Total Addressable Market):** $2.8B -- Global HR compliance software market (Gartner, 2025) intersected with AI governance ($4.3B by 2030). Companies using AI in hiring that need compliance tooling.

**SAM (Serviceable Available Market):** $340M -- US and EU enterprises with 500+ employees using AI in hiring workflows, subject to at least one hiring AI regulation. Approximately 12,000 companies.

**SOM (Serviceable Obtainable Market, 12 months):** $600K-$1.2M -- 50-100 mid-market companies at $1K/month average, acquired through compliance urgency around August 2026 EU AI Act deadline and NYC LL144 enforcement actions.

**Why now:** NYC LL144 enforcement fines started 2024. Illinois HB 3773 live January 2026. Colorado CAIA live June 2026. EU AI Act high-risk deadline August 2026. Companies are getting fined NOW and the window for panic-buying solutions is open.

---

## Competitive Landscape

| Competitor | What They Do | What They Don't Do |
|---|---|---|
| Credo AI | Model governance platform | No shadow AI detection, no hiring-specific checks |
| Holistic AI | Bias auditing for deployed models | Only audits sanctioned tools, misses informal AI use |
| HireVue | AI interviewing with built-in bias tools | Only governs their own tool, not shadow usage |
| Pymetrics/Harver | Assessment platforms with fairness baked in | Closed ecosystem, no cross-tool visibility |
| OneTrust | Privacy/GRC expanding to AI | Enterprise-heavy, no hiring-specific shadow AI detection |
| AIR Blackbox | Code compliance scanner | Currently scans code, not workplace AI usage patterns |

**The gap:** Every competitor assumes AI usage happens through sanctioned, deployed tools. Nobody detects the recruiter who pastes 50 resumes into ChatGPT and writes "not a culture fit" based on the output. This is the undefended attack surface.

**Positioning:** "For HR Compliance teams who need to detect unsanctioned AI usage in hiring, Shadow AI Detection is the only module that finds AI-generated evaluation language in your ATS and flags decisions made without recorded human review time. Unlike bias auditing tools that only govern deployed models, we catch the AI usage nobody knows about."

---

## Scope

### IN SCOPE (MVP)

1. **ATS Integration Scanner** -- Connect to Greenhouse, Lever, Workday, iCIMS via API. Scan recruiter notes, screening feedback, and evaluation comments for AI-generated language patterns.

2. **AI-Generated Language Detector** -- NLP classifier trained to distinguish human-written recruiter notes from AI-generated text. Key signals:
   - Formulaic evaluation structure (e.g., "demonstrates strong competency in...")
   - Uniform paragraph lengths across many candidates
   - Vocabulary sophistication inconsistent with the recruiter's historical writing
   - Presence of hedging patterns typical of LLMs ("it's worth noting that...")
   - Identical phrasing across multiple candidate evaluations

3. **Audit Gap Analyzer** -- Flag decisions where the time between resume receipt and screening decision is too short for human review (e.g., 200 resumes scored in 3 minutes). Cross-reference with ATS activity logs.

4. **Shadow AI Risk Dashboard** -- Per-recruiter and per-team view showing:
   - Likelihood of AI-generated evaluations (confidence score)
   - Decisions with suspicious timing gaps
   - Trend over time
   - Regulatory exposure summary (which laws apply based on candidate locations)

5. **Compliance Evidence Export** -- Generate PDF reports documenting shadow AI detection results for regulatory audits. Maps findings to specific regulations (LL144, HB 3773, FEHA, CAIA).

### OUT OF SCOPE (v1)

- Browser extension monitoring (privacy concerns, requires MDM deployment)
- Email scanning for AI-assisted communications
- Real-time blocking of LLM usage (this is a detection tool, not a blocker)
- Non-hiring AI usage detection (focus on hiring vertical only)
- Integration with HRIS systems (just ATS for MVP)
- On-premise deployment (cloud SaaS only for MVP)

---

## Technical Architecture

### High-Level System Design

```
                    +--------------------+
                    |   Shadow AI        |
                    |   Dashboard (Web)  |
                    +--------+-----------+
                             |
                    +--------v-----------+
                    |   API Gateway      |
                    |   (FastAPI)        |
                    +--------+-----------+
                             |
              +--------------+--------------+
              |              |              |
    +---------v----+ +------v-------+ +----v-----------+
    | ATS Connector| | AI Language  | | Audit Gap      |
    | Service      | | Detector     | | Analyzer       |
    +---------+----+ +------+-------+ +----+-----------+
              |              |              |
              |     +--------v---------+    |
              +---->| Analysis Engine  |<---+
                    | (Orchestrator)   |
                    +--------+---------+
                             |
                    +--------v---------+
                    | PostgreSQL       |
                    | (Findings Store) |
                    +------------------+
```

### Component Details

**1. ATS Connector Service**
- OAuth2 integrations with Greenhouse, Lever, Workday Recruiting, iCIMS
- Polls for new screening events on configurable intervals (default: every 4 hours)
- Normalizes data into a common schema: `{recruiter_id, candidate_id, action_type, text_content, timestamp, source_ats}`
- Respects ATS API rate limits
- Stores raw data with encryption at rest

**2. AI Language Detector**
- Fine-tuned classifier (base: ModernBERT or DeBERTa-v3-large)
- Training data: 10K+ paired examples of human-written vs AI-generated recruiter notes
- Features extracted:
  - Perplexity score (low perplexity = likely AI-generated)
  - Burstiness score (uniform = likely AI; variable = likely human)
  - Vocabulary fingerprint (compare to recruiter's historical writing)
  - Structural analysis (paragraph count, sentence length variance)
  - Hedging phrase density
  - Cross-candidate similarity (same recruiter using near-identical language for different candidates)
- Output: `{is_ai_generated: bool, confidence: float, evidence: [str]}`
- Target: 85%+ precision, 80%+ recall
- Model runs on-device option available (ONNX export for privacy-sensitive customers)

**3. Audit Gap Analyzer**
- Compares timestamps: resume_received_at vs. screening_decision_at
- Flags physically impossible review speeds (e.g., 200 resumes in 5 minutes)
- Cross-references with ATS login sessions (was the recruiter even logged in?)
- Detects batch patterns (20 candidates all scored at the same timestamp)
- Statistical model for "reasonable review time" based on role complexity and document length

**4. Analysis Engine (Orchestrator)**
- Receives normalized events from ATS Connector
- Runs AI Language Detector and Audit Gap Analyzer in parallel
- Combines signals into a composite Shadow AI Risk Score per decision
- Applies regulatory mapping (which laws apply based on candidate's location, company HQ, job location)
- Stores findings in PostgreSQL with full audit trail
- Triggers alerts when risk exceeds configurable thresholds

**5. Dashboard**
- React frontend (or Next.js for SSR)
- Team-level view: aggregate shadow AI risk by department, recruiter, time period
- Drill-down: individual recruiter's flagged decisions with evidence
- Regulatory exposure view: map flagged decisions to specific laws
- Export: PDF compliance reports, CSV data exports
- Role-based access: Compliance Officer (full), HR Manager (team), Recruiter (self)

### Data Flow

```
1. ATS Connector polls Greenhouse/Lever/Workday every 4 hours
2. New screening events normalized to common schema
3. Text content sent to AI Language Detector (async)
4. Timestamps sent to Audit Gap Analyzer (async)
5. Results combined by Analysis Engine
6. Findings stored in PostgreSQL
7. Dashboard queries findings via API
8. Alerts sent via email/Slack when thresholds exceeded
9. Compliance reports generated on-demand or scheduled
```

### Privacy and Security

- **No candidate PII in detection model.** The classifier only analyzes writing style, not candidate data. Candidate names, emails, and demographics are stripped before analysis.
- **Encryption at rest** for all stored ATS data (AES-256).
- **SOC 2 Type II** target for GA launch (required for enterprise sales).
- **Data residency options** for EU customers (GDPR compliance).
- **On-device model option** for customers who cannot send ATS data to cloud.

### Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| API | FastAPI (Python) | Jason's stack, async support, auto-docs |
| Database | PostgreSQL | Relational queries for compliance reporting |
| AI Detector | Fine-tuned ModernBERT | Best accuracy/speed tradeoff for text classification |
| Queue | Redis + Celery | Async processing of ATS events |
| Dashboard | Next.js + Tailwind | SSR for SEO, matches airblackbox.ai stack |
| Hosting | Vercel (frontend) + Railway/Fly.io (backend) | Cost-effective for MVP, scales later |
| ATS APIs | OAuth2 per vendor | Standard auth for Greenhouse, Lever, Workday |

---

## Business Model

**Pricing tiers:**

| Tier | Price | Includes |
|---|---|---|
| Starter | $499/month | 1 ATS integration, up to 25 recruiters, monthly compliance report |
| Professional | $999/month | 2 ATS integrations, up to 100 recruiters, weekly reports, Slack alerts |
| Enterprise | Custom (target $2,500-5,000/month) | Unlimited ATS, unlimited recruiters, on-device model, SOC 2 report, dedicated support |

**Value metric:** Per-recruiter pricing with ATS integration count as the tier gate.

**Justification:** A single LL144 violation fine starts at $500 per candidate affected. One unaudited AI screening batch of 100 candidates = $50K exposure. This tool pays for itself after catching one incident.

**Annual discount:** 2 months free (10 months at monthly rate).

---

## Go-to-Market Strategy

**Beachhead market:** Mid-market companies (500-5,000 employees) with recruiting teams of 10-50 people, headquartered in NYC, California, or Illinois, already using Greenhouse or Lever. These companies face immediate regulatory exposure and have budget authority at the HR/Compliance level.

**Launch sequence:**

| Week | Action |
|---|---|
| 1-2 | Publish "Shadow AI in Hiring" research report (drives waitlist signups) |
| 3-4 | Launch waitlist landing page at airblackbox.ai/shadow-ai |
| 5-8 | Build MVP (ATS connector for Greenhouse + AI language detector) |
| 9-10 | Onboard 5 design partners (free, in exchange for feedback + case study) |
| 11-12 | Iterate based on design partner feedback |
| 13-16 | GA launch with Greenhouse + Lever support |

**Distribution channels:**

1. **Primary: LinkedIn + HR compliance communities.** Jason's recruiting background gives credibility. Target: SHRM chapters, HR Tech conferences, compliance officer LinkedIn groups.
2. **Secondary: Content marketing.** Publish the research report on shadow AI prevalence. Pitch to HR tech publications (TLNT, ERE, HR Brew).
3. **Tertiary: Partnership with ATS vendors.** Greenhouse and Lever have marketplace/integration directories. Get listed.

**Unfair advantage:** Jason has 13+ years of recruiting experience (Meta, AWS, agency). He knows exactly how recruiters use AI informally because he has been in those rooms. No pure-tech founder has this domain credibility.

---

## Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| AI detection accuracy below 85% | Product trust destroyed | Medium | Invest heavily in training data. Start with conservative thresholds (high precision, accept lower recall). Let customers tune sensitivity. |
| ATS API access denied or limited | Cannot get data to analyze | Medium | Start with Greenhouse (most open API). Build browser-extension fallback for closed ATSs. Offer manual CSV upload as baseline. |
| Privacy backlash from recruiters | Adoption blocked by recruiting teams | High | Frame as "compliance protection" not "surveillance." Show recruiters their own risk exposure. Give recruiters visibility into their own data. |
| Enterprise sales cycle too long | Revenue delayed beyond 90 days | High | Target mid-market (shorter cycles). Use waitlist + design partner model to compress timeline. Offer month-to-month billing. |
| Regulatory landscape changes | Checks become outdated | Low | Modular rule engine. Each jurisdiction is a plugin. New laws = new config, not new code. |
| Solo founder capacity | Cannot build all of this alone | High | MVP is Greenhouse + detector only. Everything else is phase 2. Hire a contractor for frontend if needed. |

---

## Open Questions

1. **Product vs. feature:** Is this a standalone product (ShadowScan, HireGuard) or an AIR Blackbox module? Standalone has better positioning but splits Jason's brand. Module leverages existing credibility but confuses the ICP (developers vs. HR).

2. **Detection approach priority:** Start with AI language detection (NLP classifier) or audit gap analysis (timestamp heuristics)? Gap analysis is simpler to build and has zero false positives (impossible review speed is impossible review speed). Language detection is higher value but harder to get right.

3. **ATS vendor priority:** Greenhouse first (best API, most mid-market adoption) or Lever (simpler API, growing fast) or Workday (biggest enterprise install base, hardest API)?

4. **On-device vs. cloud:** The code scanner is local-first (privacy moat). Should shadow AI detection also be local-first? Hard to do when the data source is a cloud ATS. Hybrid model (cloud connector, on-device analysis) is possible but complex.

5. **Pricing validation:** Is $499/month the right starting price for mid-market HR compliance? Need 5 conversations with buyers before committing.

---

## Recommended Next Steps (Priority Order)

1. **Validate demand before building.** Write the "Shadow AI in Hiring" research report. Publish on LinkedIn. Launch a waitlist page. Target: 50 signups before writing code.

2. **Build the audit gap analyzer first.** Timestamp-based detection is deterministic (no ML needed), ships in 1-2 weeks, and has zero false positives. This alone is valuable -- "your recruiter reviewed 200 resumes in 3 minutes" is a powerful finding.

3. **Start Greenhouse API integration.** Apply for API partner access. Build the OAuth flow and data normalization layer.

4. **Collect training data for AI language detector.** Partner with 2-3 companies to get anonymized recruiter notes (human-written + suspected AI-generated). Need 10K+ examples for a reliable classifier.

5. **Decide standalone vs. module.** This decision can wait until demand is validated. Build the MVP under the AIR Blackbox brand. Spin out later if the market justifies it.

---

## Timeline

| Phase | Duration | Deliverable |
|---|---|---|
| Phase 0: Validation | 2 weeks | Research report published, waitlist live, 50 signups |
| Phase 1: Audit Gap MVP | 3 weeks | Greenhouse connector + timestamp-based shadow AI detection |
| Phase 2: AI Detector | 4 weeks | NLP classifier for AI-generated language detection |
| Phase 3: Dashboard | 2 weeks | Web dashboard with compliance reporting |
| Phase 4: GA Launch | 1 week | Public launch, pricing live, design partners convert to paid |

**Total to GA: ~12 weeks from start**

---

*This document is a product specification, not legal advice. Consult with legal counsel before making compliance claims to customers.*
