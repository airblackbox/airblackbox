# Day 2 Scan Results

Langfuse was TypeScript (2,100+ TS files, zero Python). Replaced with RAGFlow (76K stars, Python RAG engine).

---

## Superlinked (15K+ stars) - Python AI Search Framework

**Score: 2.5%** (75/3000) across 500 Python files scanned (609 total)

| EU AI Act Article | What It Checks | Files Passing |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | **0.0%** (0/500) |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | **3.2%** (16/500) |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | **8.8%** (44/500) |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | **0.0%** (0/500) |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | **0.0%** (0/500) |
| Art. 15 (Security) | Injection defense, output validation | **3.0%** (15/500) |

Frameworks detected: OpenAI

**Takeaway**: Superlinked has almost zero compliance infrastructure. No logging, no oversight, no risk management. The only bright spot is some type hinting (Art. 11 at 8.8%). This is a framework handling search and recommendations (potentially sensitive data) with no audit trail whatsoever.

---

## RAGFlow (76K+ stars) - Python RAG Engine

**Score: 7.9%** (238/3000) across 500 Python files scanned (736 total)

| EU AI Act Article | What It Checks | Files Passing |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | **1.0%** (5/500) |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | **7.6%** (38/500) |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | **30.6%** (153/500) |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | **0.4%** (2/500) |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | **4.8%** (24/500) |
| Art. 15 (Security) | Injection defense, output validation | **3.2%** (16/500) |

Frameworks detected: OpenAI, RAG, CrewAI

**Takeaway**: Better documentation coverage than Superlinked (30.6% vs 8.8%), and some data governance patterns. But still near-zero on logging and risk management. For a RAG engine processing enterprise documents, the 0.4% record-keeping score is concerning.

---

## Full Comparison Table (All Scans)

| Project | Stars | Score | Art. 9 | Art. 10 | Art. 11 | Art. 12 | Art. 14 | Art. 15 |
|---|---|---|---|---|---|---|---|---|
| **AIR Blackbox** | 0.1K | **91%** | High | High | High | High | High | High |
| **LiteLLM** | 23K+ | **48%** | Low | Med | Med | Med | Med | Low |
| **Browser Use** | 79K+ | **9.4%** | 1.1% | 5.0% | 26.0% | 0.3% | 12.2% | 12.2% |
| **RAGFlow** | 76K+ | **7.9%** | 1.0% | 7.6% | 30.6% | 0.4% | 4.8% | 3.2% |
| **Superlinked** | 15K+ | **2.5%** | 0.0% | 3.2% | 8.8% | 0.0% | 0.0% | 3.0% |

---

## Fork Commands (run on your Mac)

```bash
# Fork Superlinked
gh repo fork superlinked/superlinked --org airblackbox --clone=false

# Fork RAGFlow (replacement for Langfuse which was TypeScript)
gh repo fork infiniflow/ragflow --org airblackbox --clone=false
```

Then add the compliance scan workflow to each:

```bash
for REPO in superlinked ragflow; do
  cd ~/Desktop
  gh repo clone airblackbox/$REPO -- --depth 1
  cd $REPO
  mkdir -p .github/workflows
  cat > .github/workflows/compliance.yml << 'EOF'
name: EU AI Act Compliance Scan
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  compliance-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install AIR Blackbox
        run: pip install air-blackbox
      - name: Run EU AI Act Compliance Scan
        run: |
          echo "Scanning for EU AI Act compliance..."
          air-blackbox comply --scan . --no-llm --format table --no-save --verbose 2>&1 || true
      - name: Generate JSON Report
        run: |
          air-blackbox comply --scan . --no-llm --format json --no-save > compliance-report.json 2>/dev/null || true
          cat compliance-report.json
      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: compliance-report
          path: compliance-report.json
EOF
  git add .github/workflows/compliance.yml
  git commit -m "Add EU AI Act compliance scan workflow"
  git push
  cd ..
done
```

Then trigger:

```bash
gh workflow run compliance.yml --repo airblackbox/superlinked
gh workflow run compliance.yml --repo airblackbox/ragflow
```
