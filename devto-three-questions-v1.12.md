# Dev.to Article — "The Three Questions..." (community-first redraft)

**Target publish date**: 1-2 days after the Show HN post lands.

---

## ARTICLE METADATA

**Title**: Three Questions Every EU AI Act Auditor Will Ask About Your Python AI Agent

**Tags** (max 4): `#ai` `#opensource` `#python` `#euaiact`

**Cover image**: Terminal screenshot of `air-blackbox comply --scan` showing mixed `PASS` / `WARN` / `FAIL` results across Article 13, 14, and 15 checks. Alt text: "Terminal output from AIR Blackbox scanner showing EU AI Act Articles 9 through 15 being checked in a Python AI codebase."

---

## ARTICLE BODY

The EU AI Act's high-risk enforcement deadline is August 2, 2026. That is 109 days from today.

If your Python code runs an AI agent that makes decisions affecting someone's money, healthcare, job, housing, or insurance, those decisions are about to become legal records. The system producing them has to prove three things. This post walks through those three questions, why most Python AI codebases cannot answer them, and what a small community of open-source developers is building to close the gap.

I am one of those developers, and I want to be up front: the tool I am about to describe stands on work done by others. I will credit them throughout.

## About the scanner

[AIR Blackbox](https://github.com/airblackbox/airblackbox) is the flight recorder for autonomous AI agents. Record, replay, enforce, audit. It is Apache 2.0, runs locally, and finishes a full scan in under ten seconds.

### Install

```bash
pip install air-blackbox
```

### Run your first scan

```bash
air-blackbox comply --scan .
```

### Expected output (abbreviated)

```text
Article 9  — Risk Management              PASS (3/3 checks)
Article 10 — Data Governance              WARN (2/3 checks)
Article 11 — Technical Documentation      PASS (4/4 checks)
Article 12 — Record-Keeping               FAIL (2/5 checks)
Article 13 — Transparency                 WARN (4/6 checks)
Article 14 — Human Oversight              PASS (3/3 checks)
Article 15 — Accuracy & Robustness        FAIL (3/6 checks)
```

Every `FAIL` and `WARN` line includes a fix hint pointing at the specific code location and the specific regulatory clause.

Now let us go through the three questions.

## Question 1: Is this the same agent that acted yesterday?

An AI agent running a continuous decision loop, a `while True`, a scheduled runner, or a tick-based pattern is almost certainly executing in a different process today than yesterday. It reloaded memory from some store. It fetched its tool set. It started producing outputs.

How does a regulator know the agent producing today's loan denial is the same agent that was approved in last month's conformity assessment? How do you prove a compromised environment did not load tampered memory and produce a subtly different agent wearing the same name?

This is the agent identity continuity gap. The [NIST RFI on AI Agent Security (Docket NIST-2025-0035)](https://www.federalregister.gov/documents/2026/01/08/2026-00206/request-for-information-regarding-security-considerations-for-artificial-intelligence-agents) names it explicitly. The FINOS AI Governance Framework response to that RFI treats it as a primary unresolved problem.

### The community is already solving this

Three open standards exist today, built by different people for different use cases, all interoperable:

1. [**air-trust**](https://github.com/airblackbox/air-trust): Ed25519 agent identity keys and HMAC-SHA256 audit chain. What we ship.
2. [**AAR (Agent Action Receipt)**](https://github.com/Cyberweasel777/agent-action-receipt-spec): per-action Ed25519 signing. Designed by [@Cyberweasel777](https://github.com/Cyberweasel777).
3. [**SCC (Session Continuity Certificate)**](https://www.npmjs.com/package/botindex-aar): session-level identity with Merkle memory roots, capability hash lineage, and prior-session chaining. Co-designed by [@botbotfromuk](https://github.com/botbotfromuk) and [@Cyberweasel777](https://github.com/Cyberweasel777) in a [public FINOS thread](https://github.com/finos/ai-governance-framework/issues/266).

AIR Blackbox v1.12.0 detects all three. The goal is not to push our scheme, it is to give your code a clean pass if you have adopted any industry-recognized identity binding.

### What a failing scan looks like

If your code is an autonomous agent and none of these schemes are in use, the scanner reports:

```text
Article 12 — Record-Keeping
  FAIL  Agent identity binding
        Autonomous agent detected in 3 file(s) (agent.py, tick.py, loop.py)
        but no stable cryptographic identity binding found.
        Checked for: air-trust, AAR, SCC.
```

### The simplest fix using air-trust

Persist a stable signing key across restarts so every tick is provably signed by the same agent:

```python
from pathlib import Path
import air_trust

KEY_PATH = Path.home() / ".air-trust" / "keys" / "my-agent-ed25519.key"

identity = air_trust.AgentIdentity(
    agent_name="my-agent",
    owner="team@company.com",
    agent_version="1.0.0",
)

def tick():
    with air_trust.trust(identity):
        make_decision()
```

If you would rather use AAR or SCC, the scanner still passes as long as the library is imported and the key path is persistent. Pick what fits your stack.

## Question 2: Will it behave the same way tomorrow?

Earlier this month, Atherik was acquired. They solve this problem at runtime: AI models give different outputs on different GPUs, driver versions, and cuDNN settings. The acquisition is the market confirming the gap is real.

Runtime solutions help if you can afford them. Most teams cannot. And for SR 11-7 model validation, the Federal Reserve guidance governing model risk management in US financial services, reproducibility is a mandatory audit requirement, not an optional feature.

### What reproducibility failure looks like

Same model, same seed, same input, on two different GPUs:

```python
import torch

model = SomeModel()
tensor = torch.randn(10, 10).cuda()
output = model(tensor)
```

Run this on an NVIDIA A100 and on an NVIDIA H100 with identical PyTorch 2.4 and cuDNN 8.9. The two outputs will differ. cuDNN picks different kernels based on hardware capabilities. The model is no longer deterministic. That is an EU AI Act Article 15 robustness violation and an SR 11-7 validation failure.

### What the scanner checks

AIR Blackbox v1.12.0 added three checks for this. To my knowledge, these are the first of their kind in compliance tooling. If you know of another open-source tool doing this, please tell me, I want to credit it and learn from it.

### Check 1: RNG seeds across all sources

The scanner looks for seed setting across Python's `random`, NumPy, PyTorch CPU, PyTorch CUDA, TensorFlow, and JAX. Missing any one breaks reproducibility. Partial coverage warns, missing all of them in an ML codebase fails.

### Check 2: Deterministic algorithm flags

Seeds alone are not enough. cuDNN defaults to picking the fastest kernel, which is often non-deterministic. TensorFlow ops behave the same way. The scanner looks for these flags in your Python code and in your `.env`, Dockerfile, YAML, and shell scripts:

```python
import os
import torch

torch.use_deterministic_algorithms(True)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
```

TensorFlow equivalent:

```python
import os
import tensorflow as tf

tf.config.experimental.enable_op_determinism()
os.environ['TF_DETERMINISTIC_OPS'] = '1'
```

### Check 3: Hardware abstraction

Hardcoded `.to("cuda")` without a capability fallback crashes on CPU-only, Apple Silicon, or AMD hardware. Worse, it silently produces different outputs when you migrate between GPU generations.

Flagged as non-compliant:

```python
model = SomeModel().to("cuda")
```

Compliant:

```python
import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = SomeModel().to(device)
```

None of these checks require GPU hardware to run. The scanner reads your code, flags the anti-patterns, and you fix them at CI/CD time before a regulator, auditor, or on-call engineer finds them in production.

## Question 3: Can the user understand why it made this decision?

Article 13 of the EU AI Act covers transparency. Six sub-requirements:

- 13(2): instructions for use
- 13(3)(a): identity of the provider
- 13(3)(b): characteristics, capabilities, and limitations
- 13(3)(c): changes to the system after conformity assessment
- 13(3)(d): human oversight measures including output interpretation
- Article 50: users must be informed they are interacting with AI

Most compliance tools skip Article 13 because it is documentation-heavy and hard to automate. AIR Blackbox v1.12.0 ships what I believe is the first Article 13 static scanner. Again, if I am wrong, please tell me so I can credit the prior work.

### What the Article 13 scan looks like

```text
Article 13 — Transparency and Provision of Information
  PASS   AI disclosure to users
  FAIL   Capability and limitation documentation
         No MODEL_CARD.md, SYSTEM_CARD.md, or capability docs found
  WARN   Instructions for use
         Only README.md found. Article 13(2) expects dedicated instructions
  PASS   Provider identity disclosure
  WARN   Output interpretation support
         No confidence scores, rationale, or explanation patterns detected
  PASS   Change logging and versioning
```

Each check maps to a specific clause. Each failure comes with a fix hint. The output interpretation check catches agents that return decisions without any reasoning trace, confidence score, or rationale. In my experience this is the most common gap in current Python AI codebases.

### A concrete example

A Regulation B compliant credit decision needs to be explainable to the applicant. An agent returning a boolean `approved` / `denied` without rationale fails this.

Flagged version:

```python
def predict_creditworthiness(applicant):
    return model.predict(applicant)
```

Passing Article 13(3)(d):

```python
def predict_creditworthiness(applicant):
    prediction = model.predict(applicant)
    confidence = model.predict_proba(applicant).max()
    reasoning = generate_reasoning_trace(applicant, prediction)
    return {
        "decision": prediction,
        "confidence_score": confidence,
        "rationale": reasoning,
    }
```

## The pattern holds across every industry

Every industry where AI makes consequential decisions follows the same structure:

1. A traditionally analog market goes digital.
2. AI gets embedded in the decision-making layer.
3. Those AI decisions fall under EU AI Act Annex III or Colorado SB 205.
4. Nobody audits the AI layer for compliance.
5. The regulatory deadline is months away, not years.

My [previous post](https://dev.to/shotwellj/the-unaudited-ai-layer) walked through tokenized real estate. 1.4 trillion dollar projected 2026 market. 80 plus platforms globally. Zero of them scanning their AI systems for compliance. The pattern holds everywhere:

- **Healthcare**: AI-assisted clinical decisions are Annex III high-risk. Most clinical AI systems have no agent identity binding, no determinism flags, no structured output interpretation.
- **Financial services**: credit underwriting, trading signals, fraud detection. SR 11-7 requires reproducibility. The hardware determinism check alone flags violations in most codebases.
- **Insurance**: underwriting, claims, risk scoring. Annex III high-risk. Article 13 transparency obligations apply directly.
- **Hiring and HR**: resume screening, interview scoring. Explicitly listed in Annex III. Agent identity continuity matters because hiring decisions affect protected classes.

The opportunity is not any single industry. It is the open-source compliance infrastructure underneath all of them, and that infrastructure is being built in public, by people like the ones I credited above, right now.

## What this tool is not

This part matters. A good compliance scanner cannot be the only thing standing between your AI agent and a regulator.

- This checks technical requirements, not legal compliance. It is a linter, not a lawyer.
- Passing every check does not mean you are legally compliant. It means your code implements the technical controls the regulation references.
- Legal interpretation is your counsel's job.
- Static analysis cannot catch every runtime issue. Pair it with trust-layer integrations for runtime evidence.
- Pattern-based detection has false positives. If you see one, report it, it makes the scanner better.

## How to help

If you read this far, you probably work on AI systems that will need to pass an audit. The scanner only gets better with your feedback.

- Try it. `pip install air-blackbox && air-blackbox comply --scan .`
- If it misses a pattern, [open an issue](https://github.com/airblackbox/airblackbox/issues). Include the code pattern and the article it should map to. Every issue is a new check.
- If it produces a false positive on your code, [open an issue](https://github.com/airblackbox/airblackbox/issues). Every correction flows into training data for a fine-tuned compliance model, so false positives become easier to catch next time.
- If you are building in the same space (identity, determinism, audit trails), I would like to coordinate. Ping me on the repo or on [@jshotwell](https://github.com/jshotwell).

## Try it

```bash
pip install air-blackbox
cd /path/to/your/ai/project
air-blackbox comply --scan . -v
```

### Useful links

- Repo: [github.com/airblackbox/airblackbox](https://github.com/airblackbox/airblackbox)
- PyPI: [pypi.org/project/air-blackbox](https://pypi.org/project/air-blackbox)
- Docs and demos: [airblackbox.ai](https://airblackbox.ai)
- Interactive browser demo: [airblackbox.ai/demo/hub](https://airblackbox.ai/demo/hub)

### Thanks

- [@botbotfromuk](https://github.com/botbotfromuk) and [@Cyberweasel777](https://github.com/Cyberweasel777) for the SCC and AAR specs that v1.12.0 detects.
- The [FINOS AI Governance Framework](https://github.com/finos/ai-governance-framework) maintainers, whose public thread on NIST RFI Docket NIST-2025-0035 shaped a big part of this release.
- Everyone who has filed an issue on the scanner. Every correction is a data point.

109 days to August 2, 2026. Run the scan. See what is missing. Fix it before someone else's audit does it under pressure.

---

## REDRAFT NOTES

### What changed from the first version

- **Opened with community framing, not solo builder**: the new intro explicitly says "I stand on work done by others" and credits them before the first code block.
- **Removed em dashes**: per elite-dev-advocate rules and jason-preferences.
- **Proper H2/H3 structure**: every code block now has an explicit heading above it, which fixes the Dev.to accessibility warnings about code comments being interpreted as headings.
- **Code comments moved to prose**: the `# Machine A / # Machine B` and `# output on A != output on B` comments are now inline explanations outside the code blocks. That fixes the accessibility flags AND makes the content easier to skim.
- **Every code block has a language tag**: `bash`, `python`, `text`. No unlabeled blocks.
- **Expected output shown for the install command**: the "Expected output (abbreviated)" section gives developers something to compare against on their first run.
- **Named acknowledgements of the open-source community twice**: once in the intro, once in the "Thanks" section at the bottom.
- **Added a "What this tool is not" section**: buying-in with the community means being honest about limits. This section earns trust by preempting skepticism.
- **Added a "How to help" section with three concrete asks**: try it, open an issue, coordinate if you are building in the same space. Community buy-in requires explicit invitations to contribute.
- **Replaced "Jason Shotwell, building AIR Blackbox" signoff with a close that focuses on the work, not the builder**.

### Pre-publish checklist

- Verify `109 days` is still accurate on publish day (run `python -c "from datetime import date; print((date(2026,8,2)-date.today()).days)"` the morning of)
- Verify the Atherik acquisition reference ("earlier this month") is still within April 2026
- Confirm the URL for your previous Dev.to post is correct
- Verify the SCC repo link at github.com/Cyberweasel777/agent-action-receipt-spec resolves (check before publishing)
- Verify the FINOS issue link github.com/finos/ai-governance-framework/issues/266 resolves
- Upload terminal screenshot as cover image with the alt text provided above
- Run the `pip install air-blackbox && air-blackbox comply --scan .` command on a clean Mac and confirm the output matches what is shown in the article

### Accessibility check

- All code blocks have language tags (prevents code comments from being flagged as headings)
- Every H2 section has a descriptive name (not just a number or single word)
- Cover image includes suggested alt text
- No relative time references without concrete dates (August 2, 2026 always appears near "109 days")
- No color-only information conveyance
