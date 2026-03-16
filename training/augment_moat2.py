#!/usr/bin/env python3
"""
Augment Phase 18-25 training data with variations and instruction diversity.
Multiplies seed examples into thousands of training examples.
"""

import json
import random
import hashlib
import re

# ── Instruction diversity pools ──

AUGMENT_INSTRUCTIONS_CODE = [
    # Full analysis
    "Analyze this code for EU AI Act compliance across all relevant articles.",
    "Perform a comprehensive EU AI Act compliance audit on this code.",
    "What EU AI Act compliance issues exist in this AI code?",
    "Review this code for EU AI Act violations and provide recommendations.",
    "Is this AI code compliant with the EU AI Act? Analyze all relevant articles.",
    # Role-specific
    "As a compliance auditor, review this code for EU AI Act issues.",
    "As a CTO preparing for EU AI Act compliance, what concerns does this code raise?",
    "As an AI safety engineer, what risks does this code present under the EU AI Act?",
    "As a legal counsel, assess this code's EU AI Act compliance status.",
    "As a DPO, evaluate this AI code for regulatory compliance.",
    # Article-specific
    "Check this code for Article 9 risk management compliance.",
    "Does this code satisfy Article 10 data governance requirements?",
    "Review this code for Article 11 technical documentation compliance.",
    "Audit this code for Article 12 record-keeping requirements.",
    "Analyze this code for Article 13 transparency and explainability obligations.",
    "Check this code for Article 14 human oversight requirements.",
    "Assess this code for Article 15 accuracy, robustness, and cybersecurity.",
    "Does this code meet Article 43 conformity assessment requirements?",
    "Review this code against Article 72 post-market monitoring obligations.",
    # Scoring / quick
    "Rate this code's EU AI Act compliance on a scale of 1-10 with justification.",
    "Give a quick compliance assessment of this AI code.",
    "What's the EU AI Act risk classification for this AI system?",
    "Identify the top 3 EU AI Act compliance gaps in this code.",
    "Is this code safe to deploy in the EU? Analyze for AI Act compliance.",
    # Framework-specific
    "Analyze this LangChain code for EU AI Act compliance.",
    "Review this CrewAI agent for regulatory compliance under the EU AI Act.",
    "Check this OpenAI API code for EU AI Act compliance gaps.",
    "Audit this Anthropic API code for EU AI Act compliance.",
    "Is this agent framework code compliant with EU AI Act requirements?",
    # Recommendation-focused
    "What changes are needed to make this code EU AI Act compliant?",
    "How would you fix this code to meet EU AI Act requirements?",
    "Provide a remediation plan for this code's EU AI Act violations.",
    "What's the minimum viable compliance path for this AI code?",
    # Risk-focused
    "What risks does this AI code pose under the EU AI Act?",
    "Could this code result in EU AI Act penalties? Analyze the violations.",
    "What's the worst-case regulatory exposure for this AI code?",
    "Assess the compliance risk level of this AI deployment.",
]

AUGMENT_INSTRUCTIONS_QA = [
    # Direct
    "Explain this topic in the context of EU AI Act compliance.",
    "What does the EU AI Act say about this?",
    "How should this be implemented for EU AI Act compliance?",
    # Role-based
    "As a compliance consultant, explain this.",
    "For our engineering team: explain this EU AI Act requirement.",
    "As a regulatory affairs specialist: answer this question.",
    "For our legal team: clarify this EU AI Act point.",
    "As an AI governance officer: explain this.",
    "For a startup CTO: what does this mean practically?",
    "For our board of directors: summarize this AI Act requirement.",
    # Context-based
    "We're preparing for EU AI Act compliance: explain this.",
    "In the context of high-risk AI systems: explain this.",
    "For an Annex III high-risk system: what does this mean?",
    "For a company deploying AI in the EU: explain this requirement.",
    "Our AI system processes personal data: how does this apply?",
]

# ── Variable renames for code augmentation ──

VARIABLE_RENAMES = [
    ("client", "api_client"), ("client", "llm_client"), ("client", "ai_client"),
    ("model", "ml_model"), ("model", "ai_model"), ("model", "base_model"),
    ("result", "output"), ("result", "response"), ("result", "prediction"),
    ("response", "answer"), ("response", "reply"), ("response", "completion"),
    ("agent", "ai_agent"), ("agent", "assistant"), ("agent", "bot"),
    ("task", "job"), ("task", "assignment"), ("task", "work_item"),
    ("crew", "team"), ("crew", "pipeline"), ("crew", "workflow"),
    ("data", "records"), ("data", "dataset"), ("data", "input_data"),
    ("user", "person"), ("user", "applicant"), ("user", "customer"),
    ("query", "question"), ("query", "prompt"), ("query", "request"),
    ("features", "attributes"), ("features", "inputs"), ("features", "predictors"),
    ("logger", "log"), ("logger", "audit_logger"),
    ("monitor", "tracker"), ("monitor", "watcher"), ("monitor", "observer"),
    ("reviewer", "auditor"), ("reviewer", "overseer"), ("reviewer", "supervisor"),
]

FRAMEWORK_SWAPS = [
    ("gpt-4", "gpt-4-turbo"), ("gpt-4", "gpt-4o"), ("gpt-4", "gpt-3.5-turbo"),
    ("ChatOpenAI", "AzureChatOpenAI"),
    ("openai.chat.completions.create", "openai.chat.completions.create"),
    ("claude-3", "claude-3.5-sonnet"), ("claude-3", "claude-3-opus"),
]


def augment_code_examples(seed_path, output_path, multiplier=6):
    """Augment code examples with variable renames and instruction diversity."""
    print(f"Augmenting code examples from {seed_path} (multiplier={multiplier})...")

    with open(seed_path) as f:
        originals = [json.loads(line) for line in f]

    augmented = []
    seen_hashes = set()

    for orig in originals:
        code = orig.get("input", "")
        base_output = orig.get("output", "")

        # For Q&A examples (no code), use instruction diversity
        if not code or len(code) < 50:
            for _ in range(multiplier):
                new_inst = random.choice(AUGMENT_INSTRUCTIONS_QA)
                base_q = orig.get("instruction", "")
                # Strip prefixes to get core question
                core_q = base_q
                for prefix in ["Explain: ", "As a compliance consultant: ", "For our engineering team: ",
                              "As a DPO (Data Protection Officer): ", "For our compliance team: ",
                              "As a fairness engineer: ", "For our data science team: ",
                              "As a security engineer: ", "For our red team: ",
                              "As a documentation lead: ", "As an incident commander: ",
                              "For our SRE team: ", "As an MLOps engineer: ",
                              "For our monitoring team: ", "As a notified body assessor: ",
                              "As a human factors engineer: ", "For our UX team: ",
                              "In the context of EU AI Act compliance: ",
                              "In the context of EU AI Act Article 10: ",
                              "In the context of EU AI Act cybersecurity: ",
                              "For Article 11 documentation: ", "For Article 14 compliance: ",
                              "For Article 43 compliance: ", "For Article 62 compliance: ",
                              "For Article 72 compliance: ", "As a model governance officer: ",
                              "As an AI safety officer: ", "As a regulatory affairs manager: ",
                              "We're preparing for both GDPR and AI Act compliance: "]:
                    if core_q.startswith(prefix):
                        core_q = core_q[len(prefix):]
                        break

                new_instruction = f"{new_inst.rstrip('.')} — {core_q}" if random.random() < 0.3 else core_q
                if random.random() < 0.5:
                    new_instruction = random.choice(AUGMENT_INSTRUCTIONS_QA).rstrip('.') + ": " + core_q

                example = {"instruction": new_instruction, "input": "", "output": base_output}
                h = hashlib.md5(json.dumps(example, sort_keys=True).encode()).hexdigest()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    augmented.append(example)
            continue

        # For code examples, do variable renames + instruction diversity
        for _ in range(multiplier):
            new_code = code

            # Random variable renames (1-3)
            renames = random.sample(VARIABLE_RENAMES, min(3, len(VARIABLE_RENAMES)))
            for old, new in renames:
                if random.random() < 0.4:
                    new_code = re.sub(r'\b' + re.escape(old) + r'\b', new, new_code)

            # Random framework swaps
            if random.random() < 0.2:
                swap = random.choice(FRAMEWORK_SWAPS)
                new_code = new_code.replace(swap[0], swap[1])

            # Style changes
            if random.random() < 0.25:
                new_code = new_code.replace("print(", "logger.info(")

            if random.random() < 0.15:
                lines = new_code.split("\n")
                new_lines = []
                for line in lines:
                    new_lines.append(line)
                    if random.random() < 0.08:
                        new_lines.append("")
                new_code = "\n".join(new_lines)

            # Comment variations
            if random.random() < 0.2:
                new_code = re.sub(r'#.*$', '', new_code, flags=re.MULTILINE)

            # Dedup
            h = hashlib.md5(new_code.encode()).hexdigest()
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            # Pick random instruction
            new_inst = random.choice(AUGMENT_INSTRUCTIONS_CODE)

            augmented.append({
                "instruction": new_inst,
                "input": new_code,
                "output": base_output,
            })

    with open(output_path, "w") as f:
        for ex in augmented:
            f.write(json.dumps(ex) + "\n")

    print(f"Augmented: {len(augmented)} examples → {output_path}")
    return augmented


def generate_cross_article_examples(seed_path, output_path):
    """Generate cross-article analysis examples combining multiple compliance areas."""
    print(f"Generating cross-article examples from {seed_path}...")

    with open(seed_path) as f:
        originals = [json.loads(line) for line in f]

    # Collect code examples
    code_examples = [ex for ex in originals if ex.get("input", "") and len(ex.get("input", "")) > 100]

    cross_instructions = [
        "Analyze this code for BOTH explainability (Article 13) AND bias (Article 10) compliance.",
        "Review this code for human oversight (Article 14) AND monitoring (Article 72) requirements.",
        "Assess this code for risk management (Article 9) AND robustness (Article 15) compliance.",
        "Audit this code for documentation (Article 11) AND record-keeping (Article 12) requirements.",
        "Evaluate this code's compliance with Articles 9 through 15 comprehensively.",
        "Does this code meet both transparency (Article 13) and human oversight (Article 14) requirements?",
        "Analyze this code for bias prevention (Article 10) AND adversarial robustness (Article 15).",
        "Check this code for GDPR intersection AND EU AI Act Article 10 data governance.",
        "Review this code for conformity assessment readiness (Article 43) across all requirements.",
        "Assess whether this code would pass a conformity assessment under Article 43.",
    ]

    examples = []
    for ex in code_examples:
        for _ in range(3):
            inst = random.choice(cross_instructions)
            combined_output = f"""## Comprehensive EU AI Act Compliance Analysis

### Multi-Article Assessment

{ex.get('output', '')}

### Cross-Cutting Concerns

**Documentation Gap (Article 11)**: The system lacks technical documentation describing its design, development process, and validation methodology. This is required for any high-risk AI system.

**Record-Keeping (Article 12)**: Automated logging of system events, decisions, and their context must be implemented to enable traceability throughout the system's lifecycle.

**Post-Market Monitoring (Article 72)**: No monitoring infrastructure exists to track system performance, detect degradation, or identify emerging risks after deployment.

**Conformity Assessment Readiness (Article 43)**: The system is not ready for conformity assessment — missing documentation, testing evidence, and quality management system integration."""

            examples.append({
                "instruction": inst,
                "input": ex["input"],
                "output": combined_output,
            })

    with open(output_path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"Cross-article: {len(examples)} examples → {output_path}")
    return examples


def generate_scenario_variations(seed_path, output_path):
    """Generate domain-specific scenario variations."""
    print(f"Generating scenario variations from {seed_path}...")

    with open(seed_path) as f:
        originals = [json.loads(line) for line in f]

    domains = [
        {"name": "Healthcare", "annex": "Annex III Section 5(a)", "context": "medical diagnosis AI"},
        {"name": "Finance", "annex": "Annex III Section 5(b)", "context": "credit scoring AI"},
        {"name": "Employment", "annex": "Annex III Section 4(a)", "context": "hiring/recruitment AI"},
        {"name": "Education", "annex": "Annex III Section 3(a)", "context": "educational assessment AI"},
        {"name": "Law Enforcement", "annex": "Annex III Section 6(a)", "context": "predictive policing AI"},
        {"name": "Immigration", "annex": "Annex III Section 7(a)", "context": "asylum processing AI"},
        {"name": "Critical Infrastructure", "annex": "Annex III Section 2(a)", "context": "infrastructure management AI"},
        {"name": "Insurance", "annex": "Annex III Section 5(c)", "context": "insurance pricing AI"},
    ]

    qa_examples = [ex for ex in originals if not ex.get("input", "") or len(ex.get("input", "")) < 50]

    examples = []
    for qa in qa_examples:
        for domain in random.sample(domains, 3):  # 3 domain variations per QA
            domain_instruction = f"In the context of {domain['context']} ({domain['annex']}): {qa['instruction']}"
            domain_output = f"**Domain Context: {domain['name']} ({domain['annex']})**\n\nThis falls under high-risk classification per {domain['annex']}, requiring full compliance.\n\n{qa['output']}\n\n**Domain-Specific Note**: For {domain['context']}, this requirement is particularly stringent because {domain['name'].lower()} applications directly affect fundamental rights and safety. Penalties for non-compliance in this category can reach up to €35 million or 7% of global annual turnover."

            examples.append({
                "instruction": domain_instruction,
                "input": qa.get("input", ""),
                "output": domain_output,
            })

    with open(output_path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"Scenario variations: {len(examples)} examples → {output_path}")
    return examples


if __name__ == "__main__":
    seed_file = "phase18_to_25_moat2.jsonl"

    # 1. Heavy augmentation (6x multiplier)
    aug = augment_code_examples(seed_file, "phase18_to_25_augmented.jsonl", multiplier=6)

    # 2. Cross-article combinations
    cross = generate_cross_article_examples(seed_file, "phase18_to_25_cross_article.jsonl")

    # 3. Domain scenario variations
    scenarios = generate_scenario_variations(seed_file, "phase18_to_25_scenarios.jsonl")

    print(f"\n=== Summary ===")
    print(f"Seed examples: 180")
    print(f"Augmented: {len(aug)}")
    print(f"Cross-article: {len(cross)}")
    print(f"Scenarios: {len(scenarios)}")
    print(f"Total new: {180 + len(aug) + len(cross) + len(scenarios)}")
