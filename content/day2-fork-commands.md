# Day 2: Fork Commands

Lovable = TypeScript (dropped). Greptile = SaaS, not open-source Python (dropped).

**Replacements** (all Python, all massive):

| Repo | Stars | Why It's a Good Target |
|---|---|---|
| superlinked/superlinked | 15K+ | Python AI search/recommendation framework. Clean scan target. |
| crewAIInc/crewAI | 47K+ | AIR Blackbox already has a trust layer for CrewAI. Instant "here's the fix" angle. |
| langfuse/langfuse | 10K+ | AI observability platform. Ironic if it fails logging checks (Art. 12). |

## Run These on Your Mac

```bash
# Fork Superlinked
gh repo fork superlinked/superlinked --org airblackbox --clone=false

# Fork CrewAI
gh repo fork crewAIInc/crewAI --org airblackbox --clone=false

# Fork Langfuse
gh repo fork langfuse/langfuse --org airblackbox --clone=false
```

Then add the compliance scan workflow to each fork:

```bash
# For each repo, create the workflow file
for REPO in superlinked crewAI langfuse; do
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

Then trigger each scan:

```bash
gh workflow run compliance.yml --repo airblackbox/superlinked
gh workflow run compliance.yml --repo airblackbox/crewAI
gh workflow run compliance.yml --repo airblackbox/langfuse
```
