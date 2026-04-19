---
description: Replay recorded AI traces to detect behavioral drift between model versions
---

# /air-replay

Replay recorded AI traces and detect behavioral drift.

## Prerequisites

The replay engine requires:
- The Go gateway binary (`replayctl`) built and on PATH
- A running MinIO/S3 vault with recorded traces
- An LLM API key (OPENAI_API_KEY)

## Steps

1. Check for traces:

```bash
ls *.air.json 2>/dev/null || ls traces/*.air.json 2>/dev/null || echo "No .air.json trace files found. The gateway records these automatically during operation."
```

2. For a single trace replay:

```bash
replayctl replay <path/to/trace.air.json>
```

3. For batch replay of the last N traces:

```bash
replayctl batch ./traces/ --last 10 --format json
```

4. Present results showing:
   - Per-trace similarity score (0.0-1.0)
   - Drift detection (threshold: 0.80)
   - Original model vs replay model
   - Overall pass rate

5. If drift is detected, explain what changed:
   - Token count differences suggest structural response changes
   - Low similarity with same model suggests non-determinism
   - Low similarity with different model is expected — flag for review

6. For CI integration, point the user to the GitHub Action:

```yaml
- uses: airblackbox/airblackbox/replay-action@main
  with:
    traces-dir: ./traces
    last: 10
    vault-endpoint: ${{ secrets.VAULT_ENDPOINT }}
    vault-access-key: ${{ secrets.VAULT_ACCESS_KEY }}
    vault-secret-key: ${{ secrets.VAULT_SECRET_KEY }}
```
