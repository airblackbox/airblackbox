# Head-to-head: open-source EU AI Act code scanners

Every scanner here runs on the same programs and is scored against the same
hand-written labels. The harness, the label set, the mapping between tools
and every individual verdict are in this directory, so anyone can rerun it,
check a single answer, or argue with a label.

Run on 2026-10-15.

| Tool | Version | License |
|---|---|---|
| AIR Blackbox | 1.17.0 (PyPI) | Apache-2.0 |
| [ArkForge eu-ai-act-scanner](https://github.com/ark-forge/mcp-eu-ai-act) | 2.0.39 (PyPI) | MIT |
| [Systima Comply](https://github.com/systima-ai/comply) | 0.3.1 (npm `@systima/comply`) | Apache-2.0 |
| [Asqav compliance scanner](https://github.com/jagmarques/asqav-compliance) | 1.0.1, commit `4e3d76e` | Elastic License 2.0 |

## What is measured

**The programs.** The 144 cases of
[`eval/scanner/parity_corpus.json`](../scanner/parity_corpus.json) cover 38
practices: error handling, logging, human oversight, consent handling and so
on. Each case is written in Python, TypeScript, JavaScript, Java and Kotlin,
and each Python case is also run as a Jupyter notebook. Each is labelled by
hand: the practice is present or absent.

**Practice detection.** Each competitor is scored only on the practices it
says it checks. AIR is scored on exactly the same samples. Only programs that
import an AI SDK are scored. Some Python cases are fragments with no imports,
and a tool scoped to AI code rightly skips those. A scored sample where a tool
gives no verdict counts as not correct, because a user running that tool on
that program learns nothing.

**AI-code recognition.** For every program that imports an AI SDK, does the
tool notice it is AI code at all? Ground truth is the import lines alone,
matched by the plain patterns in `AI_IMPORTS` in `run_h2h.py`.

### How each tool's checks map to the corpus

| Tool | Its check | Corpus practice |
|---|---|---|
| ArkForge | content marking (risk "limited") | CA: AI content transparency |
| ArkForge | GDPR `consent_mechanism` pattern | GDPR consent management |
| ArkForge | GDPR `data_deletion` pattern | GDPR right to erasure |
| Systima | Article 12 logging (pass, or "structured logging detected") | Application logging |
| Systima | Article 50 AI disclosure | CO: Consumer AI disclosure, CA: AI content transparency |
| Asqav | Audit Trail | Agent action audit trail |
| Asqav | Policy Enforcement | Agent action boundaries, Usage limits / budget controls |
| Asqav | Human Oversight | Human-in-the-loop patterns |
| Asqav | Error Handling | LLM call error handling |

Sources are each tool's own code and documentation: ArkForge `server.py` and
`gdpr_module.py`, Systima `knowledge/eu-ai-act/obligations.json` and its
Article 12 and 50 checks, Asqav `src/scanner.ts` and its report text.

### What this does not measure

These checks exist in the other tools and are not scored, for or against
anyone, because no corpus case exercises them:

- **ArkForge**: Articles 9 to 15 and the GDPR documents. It checks whether
  Markdown files such as `HUMAN_OVERSIGHT.md` exist and scores their content.
- **Systima**: Article 5 prohibited-practice indicators, declared
  documentation files for Articles 9 to 14 and 27, and risk classification
  from a declared `.systima.yml`.
- **Asqav**: revocation and kill-switch patterns.

AIR checks 38 code practices in this corpus. ArkForge and Systima each have
three code-level checks that map onto it, and Asqav has five.

## Results

### Practice detection, on AI programs

| Tool | Practices | Samples | Tool correct | AIR correct |
|---|---|---|---|---|
| ArkForge | 3 | 24 | 17 (71%) | 24 (100%) |
| Systima | 3 | 26 | 19 (73%) | 26 (100%) |
| Asqav | 5 | 71 | 7 (10%) | 71 (100%) |

Restricted to the languages each tool says it reads, the gap narrows, and for
Systima it closes:

| Tool | Languages it reads | Samples | Tool correct | AIR correct |
|---|---|---|---|---|
| ArkForge | Python, TypeScript, JavaScript, Java | 16 | 13 (81%) | 16 (100%) |
| Systima | Python, TypeScript, JavaScript | 12 | 12 (100%) | 12 (100%) |
| Asqav | Python | 12 | 7 (58%) | 12 (100%) |

Per-language tables and the totals including the import-less fragments are
printed by the harness.

### AI-code recognition

Programs that import an AI SDK, recognised as AI code:

| Tool | Python | Notebook | TypeScript | JavaScript | Java | Kotlin |
|---|---|---|---|---|---|---|
| AIR Blackbox | 52/53 | 52/53 | 53/54 | 52/53 | 78/78 | 67/67 |
| ArkForge | 49/53 | 34/53 | 53/54 | 52/53 | 7/78 | 0/67 |
| Systima | 52/53 | 52/53 | 52/54 | 51/53 | 0/78 | 0/67 |
| Asqav | 48/53 | 0/53 | 0/54 | 0/53 | 0/78 | 0/67 |

AIR's three misses are real gaps in its framework list: one Python program
using LangGraph, and the TypeScript and JavaScript versions of a program using
`@openai/guardrails`.

## What the numbers mean, and what they do not

- **Most of the gap is language reach.** In Python, TypeScript and JavaScript
  the tools are close. Systima matched AIR on every sample there. The
  differences come from Java, Kotlin and notebooks, which the others mostly
  cannot read, and from how many practices each one checks.
- **We wrote the corpus.** AIR was developed against these cases, so its
  scores here are an upper bound. Its accuracy over the whole corpus is 96%:
  six cases are missed in every language and listed in
  [`SCANNER_EVAL.md`](../../SCANNER_EVAL.md). The labels were written
  before this comparison and were not changed for it.
- **The overlap is small.** 24 to 71 scored samples per competitor. Read the
  percentages as indicative.
- **The mapping is a judgement.** It is in `MAPPING` in `run_h2h.py`, with its
  sources. If a tool's check means something other than what we mapped it
  to, the fix is one line.
- **Manifests are synthesised.** Each Python and JavaScript-family sample
  gets a `requirements.txt` or `package.json` listing its imports, as a real
  project would. Systima's logging check and much of ArkForge's and Systima's
  recognition rely on these files. Java and Kotlin samples get none.
- **Two Asqav misses come from one pattern.** Its framework pattern needs a
  space or a dot after `langchain`, so `from langchain_openai import
  ChatOpenAI`, the usual LangChain import, is skipped.

Corrections are welcome as issues or pull requests, including from the tools'
maintainers.

## Reproduce

```bash
H=$(mktemp -d)
python3 -m venv $H/air  && $H/air/bin/pip install "air-blackbox==1.17.0"
python3 -m venv $H/ark  && $H/ark/bin/pip install "eu-ai-act-scanner==2.0.39"
(cd $H && npm init -y >/dev/null && npm install @systima/comply@0.3.1)
git clone https://github.com/jagmarques/asqav-compliance $H/asqav
git -C $H/asqav checkout 4e3d76e
$H/node_modules/.bin/tsc $H/asqav/src/scanner.ts --outDir $H/asqav-build \
    --module commonjs --target es2020 --esModuleInterop || true   # exits 2 on missing node types, still emits scanner.js

ARKFORGE_PYTHON=$H/ark/bin/python \
SYSTIMA_COMPLY=$H/node_modules/.bin/comply \
ASQAV_SCANNER=$H/asqav-build/scanner.js \
ASQAV_REF="asqav-compliance 1.0.1 @ 4e3d76e" \
$H/air/bin/python eval/competitors/run_h2h.py --json eval/competitors/results.json
```

`results.json` holds every verdict from every tool on every scored sample.
The run takes about three minutes, almost all of it Systima's CLI.
