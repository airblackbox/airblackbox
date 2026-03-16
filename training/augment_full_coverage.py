#!/usr/bin/env python3
"""
AIR Blackbox — Augmentation Pipeline for Phases 27-32
======================================================
Takes seed examples from generate_full_coverage.py and expands via:
1. Instruction diversity (rephrase questions)
2. Domain scenario variations (healthcare, finance, education, etc.)
3. Cross-article combinations (multi-article compliance analysis)
4. Code variable/framework swaps for code examples
"""

import json
import random
import hashlib
import re
import copy

random.seed(42)

# ═══════════════════════════════════════
# Instruction Diversity Templates
# ═══════════════════════════════════════

QA_INSTRUCTION_VARIANTS = [
    "Explain {topic}",
    "What does the EU AI Act say about {topic}?",
    "Help me understand {topic} under the EU AI Act",
    "Break down {topic} for me",
    "I need to know about {topic} for EU AI Act compliance",
    "What are the requirements for {topic}?",
    "Can you walk me through {topic}?",
    "How does {topic} work in practice?",
    "What should I know about {topic} as a developer?",
    "Summarize the EU AI Act requirements on {topic}",
    "I'm confused about {topic} — can you clarify?",
    "What's the practical impact of {topic} on my AI project?",
    "Our legal team is asking about {topic} — what do I tell them?",
    "We're preparing for an audit and need to understand {topic}",
    "What are the penalties for not complying with {topic}?",
]

CODE_INSTRUCTION_VARIANTS = [
    "Analyze this code for EU AI Act compliance:",
    "Review this code against the EU AI Act:",
    "Is this code compliant with EU AI Act requirements?",
    "Check this for AI Act violations:",
    "What EU AI Act issues does this code have?",
    "Scan this Python code for compliance problems:",
    "Run an EU AI Act compliance check on this code:",
    "Does this code meet EU AI Act standards?",
    "What would a regulator say about this code?",
    "Identify any EU AI Act risks in this code:",
    "We're deploying this in the EU — check for compliance issues:",
    "Our compliance team wants this scanned against the AI Act:",
]

# ═══════════════════════════════════════
# Domain Variations
# ═══════════════════════════════════════

DOMAINS = {
    "healthcare": {
        "use_case": "medical diagnosis assistance",
        "data_type": "patient health records",
        "stakeholder": "patients",
        "risk_area": "Annex III area 5 (essential services) and potentially Annex I (medical devices)",
        "specific_risk": "incorrect diagnosis leading to delayed treatment"
    },
    "finance": {
        "use_case": "credit scoring and loan approval",
        "data_type": "financial transaction history",
        "stakeholder": "loan applicants",
        "risk_area": "Annex III area 5(a) (creditworthiness)",
        "specific_risk": "discriminatory denial of financial services"
    },
    "employment": {
        "use_case": "resume screening and candidate ranking",
        "data_type": "job applications and CVs",
        "stakeholder": "job applicants",
        "risk_area": "Annex III area 4(a) (recruitment)",
        "specific_risk": "biased hiring decisions excluding qualified candidates"
    },
    "education": {
        "use_case": "student assessment and admissions",
        "data_type": "student performance records",
        "stakeholder": "students and parents",
        "risk_area": "Annex III area 3 (education and vocational training)",
        "specific_risk": "unfair academic evaluation or access denial"
    },
    "law_enforcement": {
        "use_case": "criminal risk assessment",
        "data_type": "criminal justice records",
        "stakeholder": "suspects and defendants",
        "risk_area": "Annex III area 6 (law enforcement)",
        "specific_risk": "biased risk profiling affecting liberty"
    },
    "immigration": {
        "use_case": "visa/asylum application assessment",
        "data_type": "immigration application records",
        "stakeholder": "asylum seekers and visa applicants",
        "risk_area": "Annex III area 7 (migration and border control)",
        "specific_risk": "unjust denial of asylum or entry"
    },
    "insurance": {
        "use_case": "insurance risk pricing",
        "data_type": "claims history and personal data",
        "stakeholder": "policyholders",
        "risk_area": "Annex III area 5(b) (insurance)",
        "specific_risk": "discriminatory premium pricing"
    },
    "infrastructure": {
        "use_case": "critical infrastructure management",
        "data_type": "sensor and telemetry data",
        "stakeholder": "public safety",
        "risk_area": "Annex III area 2 (critical infrastructure)",
        "specific_risk": "system failure affecting public safety"
    },
}

# ═══════════════════════════════════════
# Cross-Article Combinations
# ═══════════════════════════════════════

CROSS_ARTICLE_SCENARIOS = [
    {
        "instruction": "I'm deploying a vendor's high-risk AI system for {domain_use_case}. What obligations do I have as a deployer AND what should I verify the provider has done?",
        "topic_map": {
            "articles": ["Article 26 (deployer)", "Articles 16-24 (provider)", "Article 43 (conformity)"],
            "response_template": """As a deployer of a high-risk AI system for {domain_use_case}, you have a dual responsibility: your own deployer obligations AND verification that the provider met theirs.

**Your deployer obligations (Article 26):**
1. Use in accordance with provider's instructions for use
2. Assign competent human oversight personnel
3. Monitor system operation for {domain_specific_risk}
4. Ensure input data quality ({domain_data_type})
5. Inform {domain_stakeholder} that AI is being used in decisions about them
6. Retain automatically generated logs (minimum 6 months)
7. Report serious incidents to provider and authorities

**Verify provider compliance (Articles 16-24):**
1. CE marking is present (Article 48)
2. EU declaration of conformity is available (Article 47)
3. System is registered in EU database (Article 49)
4. Instructions for use are provided and complete (Article 13(3))
5. Technical documentation is available upon request
6. Provider has a quality management system (Article 17)

**For {domain_risk_area}:**
- Fundamental rights impact assessment required (Article 27)
- Data protection impact assessment required (GDPR Article 35)
- Registration of your deployment in EU database (Article 49(3))

**Red flags that the provider hasn't complied:**
- No CE marking on software/documentation
- No instructions for use document
- Cannot provide conformity assessment evidence
- No contact information for the provider or authorized representative"""
        }
    },
    {
        "instruction": "A company is using a GPAI model to build a {domain_use_case} system. Walk through the entire compliance chain from GPAI provider to deployer.",
        "topic_map": {
            "articles": ["Article 53 (GPAI)", "Articles 9-15 (high-risk)", "Article 26 (deployer)"],
            "response_template": """The compliance chain for building a {domain_use_case} system on top of a GPAI model involves three layers:

**Layer 1: GPAI Model Provider (e.g., OpenAI, Anthropic, Meta)**
Obligations under Article 53:
- Technical documentation (Annex XI)
- Downstream provider integration documentation
- Copyright compliance policy
- Training data summary (publicly available)
- If systemic risk (>10^25 FLOPS): model evaluation, risk assessment, incident reporting

**Layer 2: High-Risk System Provider (the company building the system)**
Because {domain_use_case} falls under {domain_risk_area}, the system is high-risk. Obligations:
- Article 9: Risk management system addressing {domain_specific_risk}
- Article 10: Data governance for {domain_data_type}
- Article 11: Technical documentation covering GPAI integration
- Article 12: Logging all AI decisions with auditability
- Article 13: Transparency — document capabilities and limitations for deployers
- Article 14: Human oversight mechanisms for consequential decisions about {domain_stakeholder}
- Article 15: Robustness testing including GPAI failure modes
- Article 43: Conformity assessment (self-assessment for most Annex III)
- Article 48: CE marking
- Article 49: EU database registration

**Layer 3: Deployer (the organization using the system)**
Obligations under Article 26:
- Human oversight with competent, trained staff
- Input data quality ({domain_data_type})
- Monitoring system outputs for {domain_specific_risk}
- Inform {domain_stakeholder} about AI involvement
- Fundamental rights impact assessment (Article 27)
- Log retention (minimum 6 months)
- Incident reporting to provider and authorities

**Key chain-of-custody requirement:**
Each layer must provide sufficient documentation to the next. If the GPAI provider doesn't give enough information, the high-risk system provider must document this gap. If the system provider doesn't provide adequate instructions for use, the deployer should request them before deployment."""
        }
    },
    {
        "instruction": "My AI system for {domain_use_case} was flagged as non-compliant during audit. What corrective actions do I need to take under the EU AI Act?",
        "topic_map": {
            "articles": ["Article 20 (corrective action)", "Article 62 (incident reporting)", "Article 72 (post-market monitoring)"],
            "response_template": """Non-compliance for a {domain_use_case} system ({domain_risk_area}) triggers immediate corrective action obligations:

**Immediate Steps (Article 20):**
1. Take corrective action to bring the system into conformity
2. If conformity cannot be achieved: withdraw or recall the system
3. Inform distributors, deployers, and authorized representatives
4. If the system presents a risk to {domain_stakeholder}: inform the competent authority of the Member States where the system was made available

**If serious harm has occurred (Article 62 — Serious Incident Reporting):**
A serious incident means:
- Death or serious damage to health, property, or environment
- Serious and irreversible disruption of critical infrastructure management
- Breach of fundamental rights obligations

If this applies to your {domain_use_case} system:
1. Report to market surveillance authority of the Member State where the incident occurred
2. Report IMMEDIATELY upon establishing a causal link (or reasonable likelihood)
3. Within 15 days: provide detailed report with corrective measures taken
4. Report must include: system identification, incident description, corrective measures, contact details

**Post-Market Monitoring Update (Article 72):**
After corrective action:
1. Update your post-market monitoring plan
2. Add the non-compliance finding as a known risk
3. Implement additional monitoring to detect recurrence
4. Update technical documentation to reflect changes
5. Reassess whether a new conformity assessment is needed (Article 43(4) — substantial modification)

**For {domain_specific_risk}:**
If the non-compliance specifically relates to bias or discrimination against {domain_stakeholder}:
- Conduct targeted bias testing on the corrected system
- Document the root cause analysis
- Implement ongoing demographic parity monitoring
- Consider whether affected {domain_stakeholder} should be notified and offered remediation"""
        }
    },
]

# ═══════════════════════════════════════
# Augmentation Functions
# ═══════════════════════════════════════

def augment_instruction_diversity(examples: list) -> list:
    """Generate variants with different instruction phrasings."""
    augmented = []
    for ex in examples:
        msgs = ex["messages"]
        user_msg = msgs[1]["content"]

        # Only augment Q&A examples (not code examples)
        if "```" in user_msg:
            # Code example — vary the instruction prefix
            code_block = re.search(r'```[\s\S]*?```', user_msg)
            if code_block:
                for variant in random.sample(CODE_INSTRUCTION_VARIANTS, min(3, len(CODE_INSTRUCTION_VARIANTS))):
                    new_ex = copy.deepcopy(ex)
                    new_ex["messages"][1]["content"] = f"{variant}\n\n{code_block.group()}"
                    augmented.append(new_ex)
        else:
            # Q&A — extract topic and rephrase
            # Use first 50 chars as topic proxy
            topic = user_msg[:80].strip("?").strip()
            for variant_template in random.sample(QA_INSTRUCTION_VARIANTS, min(3, len(QA_INSTRUCTION_VARIANTS))):
                new_ex = copy.deepcopy(ex)
                new_ex["messages"][1]["content"] = variant_template.format(topic=topic.lower())
                augmented.append(new_ex)

    return augmented

def generate_domain_scenarios(examples: list) -> list:
    """Generate domain-specific variations of cross-article scenarios."""
    augmented = []
    for scenario in CROSS_ARTICLE_SCENARIOS:
        for domain_key, domain in DOMAINS.items():
            instruction = scenario["instruction"].format(
                domain_use_case=domain["use_case"]
            )
            response = scenario["topic_map"]["response_template"].format(
                domain_use_case=domain["use_case"],
                domain_data_type=domain["data_type"],
                domain_stakeholder=domain["stakeholder"],
                domain_risk_area=domain["risk_area"],
                domain_specific_risk=domain["specific_risk"]
            )
            augmented.append({
                "messages": [
                    {"role": "system", "content": "You are AIR Blackbox, an EU AI Act compliance expert. Provide accurate, actionable guidance on EU AI Act compliance."},
                    {"role": "user", "content": instruction},
                    {"role": "assistant", "content": response}
                ]
            })
    return augmented

def dedup(examples: list) -> list:
    """Remove duplicates based on content hash."""
    seen = set()
    unique = []
    for ex in examples:
        h = hashlib.md5(json.dumps(ex, sort_keys=True).encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(ex)
    return unique

def main():
    # Load seed examples
    seed_file = "training/phase27_to_32_full_coverage.jsonl"
    seeds = []
    with open(seed_file) as f:
        for line in f:
            seeds.append(json.loads(line))
    print(f"Loaded {len(seeds)} seed examples")

    # Augment with instruction diversity
    instruction_variants = augment_instruction_diversity(seeds)
    print(f"Instruction diversity: {len(instruction_variants)} variants")

    # Generate domain scenario variations
    domain_scenarios = generate_domain_scenarios(seeds)
    print(f"Domain scenarios: {len(domain_scenarios)} examples")

    # Combine everything
    all_examples = seeds + instruction_variants + domain_scenarios
    all_examples = dedup(all_examples)
    print(f"Total after dedup: {len(all_examples)}")

    # Write augmented examples
    augmented_file = "training/phase27_to_32_augmented.jsonl"
    with open(augmented_file, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Written to: {augmented_file}")

    # Merge with v10 to create v11
    v10_file = "training/training_data_v10.jsonl"
    v10_examples = []
    try:
        with open(v10_file) as f:
            for line in f:
                v10_examples.append(json.loads(line))
        print(f"\nLoaded v10: {len(v10_examples)} examples")
    except FileNotFoundError:
        print(f"\nWARNING: {v10_file} not found, trying v9...")
        v9_file = "training/training_data_v9.jsonl"
        with open(v9_file) as f:
            for line in f:
                v10_examples.append(json.loads(line))
        print(f"Loaded v9: {len(v10_examples)} examples")

    # Merge
    v11_examples = v10_examples + all_examples
    v11_examples = dedup(v11_examples)

    v11_file = "training/training_data_v11.jsonl"
    with open(v11_file, "w") as f:
        for ex in v11_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\n{'='*50}")
    print(f"training_data_v11.jsonl: {len(v11_examples)} examples")
    print(f"New examples added: {len(v11_examples) - len(v10_examples)}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
