#!/bin/bash
# AIR Blackbox - EU AI Act Compliance Feature Requests
# Run this from your Mac where gh CLI is authenticated
# Usage: chmod +x submit-all-issues.sh && ./submit-all-issues.sh
#
# To submit just one: gh issue create --repo OWNER/REPO --title "..." --body "..."
# To do a dry run first: add --dry-run to each command (not a real flag, just review the output)

set -e

echo "Opening 12 EU AI Act compliance feature requests..."
echo ""

# 1. LiteLLM
echo "1/12: LiteLLM..."
gh issue create --repo BerriAI/litellm \
  --title "Feature Request: EU AI Act compliance checks for LLM gateway traffic" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, projects that route LLM traffic (like LiteLLM) will need to demonstrate compliance with Articles 9-15 for high-risk AI systems. LiteLLM is uniquely positioned to help here since it already sits in the request path and handles logging, guardrails, and cost tracking.

## What this could look like

LiteLLM already has many of the building blocks: structured logging, retry/fallback logic, and guardrails. A compliance mode could surface how well a deployment covers the key EU AI Act articles:

- **Art. 9 (Risk Management)**: Error handling and fallback patterns across providers
- **Art. 10 (Data Governance)**: PII detection/redaction in prompts before they hit provider APIs
- **Art. 11 (Documentation)**: Auto-generated system cards for multi-provider deployments
- **Art. 12 (Record-Keeping)**: Tamper-evident audit trails for all LLM calls
- **Art. 14 (Human Oversight)**: Budget controls, rate limiting, kill switches
- **Art. 15 (Security)**: Prompt injection scanning, output validation

## Context

I ran LiteLLM through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). LiteLLM scored 48% on static analysis checks, which is one of the highest scores I've seen across any project. The foundations are already there.

You can run the scan yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

LiteLLM is used as an AI gateway by teams that have EU operations. Having compliance-aware features built into the gateway layer means every team using LiteLLM gets compliance tooling for free, which is a strong differentiator against other gateway solutions.

The EU AI Act carries penalties of up to €35M or 7% of global turnover. Teams are starting to evaluate their stack for compliance readiness now.
EOF
)"
echo "  Done."

# 2. Superlinked
echo "2/12: Superlinked..."
gh issue create --repo superlinked/superlinked \
  --title "Feature Request: EU AI Act compliance checks for vector search pipelines" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, AI-powered search and recommendation systems like Superlinked will need to demonstrate compliance with Articles 9-15 for high-risk AI systems. As a framework that handles data ingestion, embedding, and retrieval, Superlinked touches several compliance-relevant areas.

## What this could look like

- **Art. 10 (Data Governance)**: Input validation and schema enforcement for ingested data, PII handling before embedding
- **Art. 11 (Documentation)**: Auto-generated documentation for search pipeline configurations
- **Art. 12 (Record-Keeping)**: Structured logging of queries, retrieval results, and relevance scores
- **Art. 14 (Human Oversight)**: Query rate limiting, result filtering controls
- **Art. 15 (Security)**: Input sanitization for search queries, adversarial robustness for embeddings

## Context

I ran Superlinked through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

Enterprise teams using Superlinked for search and recommendations in EU markets will need to demonstrate that their AI-powered retrieval systems meet the Act's requirements. Having compliance patterns built into the framework gives those teams a head start.
EOF
)"
echo "  Done."

# 3. Browser Use
echo "3/12: Browser Use..."
gh issue create --repo browser-use/browser-use \
  --title "Feature Request: EU AI Act compliance checks for browser automation agents" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, autonomous AI agents that interact with the web (like Browser Use) face unique compliance requirements. Browser automation agents take real-world actions on behalf of users, which puts them squarely in scope for Articles 9-15 of the Act, particularly around human oversight and record-keeping.

## What this could look like

- **Art. 9 (Risk Management)**: Risk classification for different action types (read-only browsing vs. form submissions vs. purchases)
- **Art. 12 (Record-Keeping)**: Tamper-evident audit trails of every page visited, action taken, and decision made
- **Art. 14 (Human Oversight)**: Configurable approval gates before high-risk actions (payments, account changes, data submissions), kill switches, action boundaries
- **Art. 15 (Security)**: Prompt injection defense when processing page content, output validation before acting

## Context

I ran Browser Use through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

Browser automation agents are among the most action-capable AI systems being built today. The EU AI Act specifically targets systems that take autonomous actions, and the 79K+ stars on this repo mean a lot of developers are building with it. Having compliance guardrails built into the framework helps every downstream project.
EOF
)"
echo "  Done."

# 4. RAGFlow
echo "4/12: RAGFlow..."
gh issue create --repo infiniflow/ragflow \
  --title "Feature Request: EU AI Act compliance checks for RAG pipelines" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, RAG systems like RAGFlow will need to demonstrate compliance with Articles 9-15. RAG pipelines that ingest documents, retrieve context, and generate responses touch multiple compliance-relevant areas including data governance, record-keeping, and accuracy.

## What this could look like

- **Art. 10 (Data Governance)**: PII detection/redaction in ingested documents, data lineage tracking
- **Art. 11 (Documentation)**: Auto-generated documentation of pipeline configurations, chunk strategies, and model choices
- **Art. 12 (Record-Keeping)**: Structured logging of retrieval decisions, which chunks were used, confidence scores
- **Art. 14 (Human Oversight)**: Configurable confidence thresholds, human review for low-confidence responses
- **Art. 15 (Security)**: Input sanitization, hallucination detection, source attribution

## Context

I ran RAGFlow through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

RAG systems are one of the most deployed AI patterns in enterprise. Teams using RAGFlow to build document Q&A, knowledge bases, and search systems for EU customers will need compliance coverage. Having it built into the framework saves every team from solving it independently.
EOF
)"
echo "  Done."

# 5. MetaGPT
echo "5/12: MetaGPT..."
gh issue create --repo geekan/MetaGPT \
  --title "Feature Request: EU AI Act compliance checks for multi-agent workflows" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, multi-agent frameworks like MetaGPT face unique compliance requirements. When multiple AI agents collaborate (product managers, architects, engineers), the compliance surface area multiplies: every agent action, every inter-agent message, and every output needs to be auditable.

## What this could look like

- **Art. 9 (Risk Management)**: Risk classification per agent role, error handling across the agent pipeline
- **Art. 12 (Record-Keeping)**: Tamper-evident audit trails of inter-agent communication and decision chains
- **Art. 14 (Human Oversight)**: Approval gates between agent phases (e.g., human review before code generation begins), budget controls per agent
- **Art. 15 (Security)**: Prompt injection defense at agent boundaries, output validation between agents

## Context

I ran MetaGPT through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

Multi-agent systems are a rapidly growing category, and MetaGPT is one of the most prominent. The EU AI Act specifically targets autonomous AI systems, and multi-agent workflows where agents delegate to other agents are exactly the kind of system regulators are focused on. Getting compliance patterns in early positions MetaGPT well for enterprise adoption in regulated markets.
EOF
)"
echo "  Done."

# 6. Deepchecks
echo "6/12: Deepchecks..."
gh issue create --repo deepchecks/deepchecks \
  --title "Feature Request: EU AI Act compliance mapping for validation checks" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, Deepchecks is naturally positioned to help teams demonstrate compliance. You already validate ML models and data, which maps directly to several EU AI Act articles. Adding explicit compliance mapping would make the connection clear for enterprise teams.

## What this could look like

- **Art. 9 (Risk Management)**: Map existing model validation checks to risk assessment requirements
- **Art. 10 (Data Governance)**: Map data validation suites to data governance requirements, add PII detection checks
- **Art. 11 (Documentation)**: Generate compliance-ready reports from check results, auto-generate model cards
- **Art. 15 (Security)**: Add adversarial robustness checks mapped to Article 15 requirements

Deepchecks already does most of this work. The feature request is really about adding an EU AI Act lens to the existing check output, so teams can point auditors to specific Deepchecks reports.

## Context

I ran Deepchecks through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

Deepchecks already validates the things the EU AI Act cares about. Making the mapping explicit turns Deepchecks into a compliance tool, not just a validation tool, which is a strong positioning for enterprise sales in EU markets.
EOF
)"
echo "  Done."

# 7. Cleanlab
echo "7/12: Cleanlab..."
gh issue create --repo cleanlab/cleanlab \
  --title "Feature Request: EU AI Act compliance mapping for data quality checks" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, data quality tools like Cleanlab become critical for compliance. Article 10 (Data Governance) specifically requires that training data meets quality criteria, and Cleanlab's data-centric approach directly addresses this.

## What this could look like

- **Art. 10 (Data Governance)**: Map Cleanlab's data quality checks (label errors, outliers, duplicates) to Article 10 requirements, generate compliance-ready reports
- **Art. 11 (Documentation)**: Auto-generate data quality documentation that satisfies Article 11's technical documentation requirements
- **Art. 9 (Risk Management)**: Flag datasets with high error rates as compliance risks

## Context

I ran Cleanlab through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

The EU AI Act's data governance requirements (Article 10) are some of the most specific and actionable in the legislation. Cleanlab already solves the hard problem of finding data quality issues. Adding explicit EU AI Act mapping turns every Cleanlab report into compliance evidence, which is a strong differentiator for enterprise adoption.
EOF
)"
echo "  Done."

# 8. Lightly AI
echo "8/12: Lightly AI..."
gh issue create --repo lightly-ai/lightly \
  --title "Feature Request: EU AI Act compliance checks for data curation pipelines" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, data curation tools like Lightly become important for compliance. As a Swiss/EU company, Lightly is directly in scope. Article 10 (Data Governance) requires that training data meets quality and representativeness criteria, which is exactly what Lightly's curation pipeline addresses.

## What this could look like

- **Art. 10 (Data Governance)**: Map Lightly's data selection and curation to Article 10 data governance requirements, generate compliance reports showing dataset composition and selection criteria
- **Art. 11 (Documentation)**: Auto-generate documentation for dataset curation decisions (why certain samples were selected/excluded)
- **Art. 12 (Record-Keeping)**: Audit trails for data curation pipelines showing provenance and selection history

## Context

I ran Lightly through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

As an EU-based company, Lightly's customers will be among the first to need compliance evidence. Data curation decisions are auditable under the Act, and having compliance-aware features built into the curation pipeline helps every downstream user demonstrate that their training data meets Article 10 requirements.
EOF
)"
echo "  Done."

# 9. FLUX (Black Forest Labs)
echo "9/12: FLUX (Black Forest Labs)..."
gh issue create --repo black-forest-labs/flux \
  --title "Feature Request: EU AI Act compliance checks for inference pipeline" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, and Black Forest Labs being based in Freiburg, Germany, FLUX falls directly under the Act's jurisdiction. The inference repo could benefit from compliance-aware patterns mapped to Articles 9-15.

## What this could look like

- **Art. 11 (Documentation)**: Model cards, system documentation, expanded docstrings (currently at 11% coverage, type hints are strong at 81%)
- **Art. 12 (Record-Keeping)**: Structured logging for inference calls (no logging framework currently detected)
- **Art. 14 (Human Oversight)**: Content filtering controls, generation rate limiting, usage tracking
- **Art. 15 (Security)**: Prompt injection defense for text-to-image prompts, output validation (watermarking is already present)

## Context

I ran FLUX through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). FLUX scored 6/44 checks passing (14%). The type hint coverage is strong, but record-keeping patterns are the biggest gap.

You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

As one of the most prominent EU-based AI companies, Black Forest Labs is likely to face early scrutiny under the Act. Having compliance patterns in the open-source inference code also helps downstream developers who build on FLUX demonstrate their own compliance.
EOF
)"
echo "  Done."

# 10. supervision (Roboflow)
echo "10/12: supervision (Roboflow)..."
gh issue create --repo roboflow/supervision \
  --title "Feature Request: EU AI Act compliance checks for computer vision pipelines" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, computer vision systems built with supervision will need to demonstrate compliance. The Act specifically calls out biometric identification and real-time monitoring as high-risk categories, which are common use cases for CV pipelines.

## What this could look like

- **Art. 9 (Risk Management)**: Risk classification for detection/tracking use cases (surveillance vs. manufacturing vs. sports analytics have different risk levels)
- **Art. 12 (Record-Keeping)**: Structured logging for detection events, tracking decisions, and zone analytics
- **Art. 14 (Human Oversight)**: Configurable confidence thresholds, human review triggers for high-stakes detections
- **Art. 15 (Security)**: Adversarial robustness testing for detection models, input validation for video streams

## Context

I ran supervision through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). supervision scored 7/44 checks passing (16%), but the documentation quality is exceptional: 98% type hint coverage and 66% docstring coverage, the best I've seen across any project.

You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

With 36K+ stars and Fortune 100 adoption, supervision is the foundation for a huge number of CV applications. Many of these run in EU markets where the Act applies. Computer vision is explicitly called out in the Act as a high-risk category. Having compliance-aware features in the library helps every downstream user.
EOF
)"
echo "  Done."

# 11. Ivy (Unify)
echo "11/12: Ivy (Unify)..."
gh issue create --repo unifyai/ivy \
  --title "Feature Request: EU AI Act compliance metadata for unified ML framework" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, and Unify being based in London, Ivy falls within scope of the Act. As a framework that unifies multiple ML backends, Ivy has a unique opportunity: compliance metadata could flow through the framework layer, giving every downstream project compliance visibility regardless of which backend they use.

## What this could look like

- **Art. 11 (Documentation)**: Expanded docstrings and type hints (currently at 24% and 45% respectively), auto-generated system cards for multi-backend deployments
- **Art. 12 (Record-Keeping)**: Framework-level logging that captures which backend handled each operation, with structured audit trails
- **Art. 14 (Human Oversight)**: Backend-agnostic budget controls and execution timeouts
- **Art. 15 (Security)**: Input validation at the framework boundary before dispatching to backends

## Context

I ran Ivy through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). 1,473 Python files scanned, 7/45 checks passing (16%).

You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

As a framework layer, Ivy can surface compliance metadata that individual backends don't provide. This is a strong differentiator: teams that use Ivy get compliance observability across all their ML backends automatically.
EOF
)"
echo "  Done."

# 12. Letta (MemGPT)
echo "12/12: Letta..."
gh issue create --repo letta-ai/letta \
  --title "Feature Request: EU AI Act compliance checks for stateful AI agents" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Summary

With the EU AI Act enforcement deadline on August 2, 2026, stateful agent frameworks like Letta face unique compliance requirements. Agents with persistent memory that learn and evolve raise specific questions under the Act around record-keeping (what did the agent remember and why?), human oversight (can you intervene in a long-running agent?), and data governance (how is stored memory handled under GDPR?).

## What this could look like

Letta already has many of the building blocks (this is one of the strongest codebases I've scanned for compliance patterns):

- **Art. 10 (Data Governance)**: PII detection/redaction for agent memory, data governance documentation for memory stores
- **Art. 12 (Record-Keeping)**: You already have action-level audit logging (22 files) and production-grade tracing (208 files). A compliance mode could make these tamper-evident with HMAC-SHA256 chains
- **Art. 14 (Human Oversight)**: Memory inspection tools, approval gates for memory mutations, agent pause/resume controls
- **GDPR**: Right-to-erasure for agent memories, data retention policies for conversation history

## Context

I ran Letta through [AIR Blackbox](https://github.com/air-blackbox/gateway), an open-source EU AI Act compliance scanner (Apache 2.0). Letta scored 17/45 checks passing (38%), one of the highest scores I've seen. Agent identity binding, injection defense, and audit trails are already present.

You can run it yourselves:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally, no data leaves your machine.

## Why this matters

Stateful agents are the frontier of AI systems, and they're the hardest to make compliant because they accumulate state over time. Letta is the leading framework here. Getting compliance patterns right for persistent memory agents positions Letta as the trusted choice for enterprise teams building in regulated markets.
EOF
)"
echo "  Done."

echo ""
echo "All 12 issues created successfully!"
echo "Check your notifications for the issue URLs."
