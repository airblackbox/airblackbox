# compliance-action

[![compliance-action](https://github.com/airblackbox/compliance-action/workflows/compliance/badge.svg)](https://github.com/airblackbox/compliance-action)

A GitHub Action that runs EU AI Act compliance checks on Python codebases in pull requests. Powered by [air-blackbox](https://pypi.org/project/air-blackbox/).

## What It Does

Automatically scans Python code for EU AI Act compliance (Articles 9–15) on every PR, posts findings as comments, and enforces score thresholds.

## Quick Start

Add this workflow to `.github/workflows/compliance.yml`:

```yaml
name: Compliance Check

on:
  pull_request:
    paths:
      - '**.py'

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: airblackbox/compliance-action@v1
        with:
          python-files: './src'
          strict: false
          articles: '9,10,11,12,14,15'
          fail-threshold: 70
```

Commit and push. The action runs on every PR and posts results as a comment.

## Inputs

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `python-files` | Yes | | Path to Python files or directory to scan (e.g., `./src`, `./app.py`) |
| `strict` | No | `false` | Exit with error if any findings detected |
| `articles` | No | `9,10,11,12,14,15` | Comma-separated EU AI Act articles to check (9, 10, 11, 12, 14, 15) |
| `fail-threshold` | No | `0` | Compliance score threshold (0–100). Fails if score is below this value |

## Outputs

| Output | Description |
|--------|-------------|
| `compliance-score` | Numeric compliance score (0–100) |
| `status` | `pass` or `fail` |
| `findings-count` | Number of findings detected |

## PR Comment Example

The action posts a comment on your PR with results:

```
## EU AI Act Compliance Check

Compliance Score: 87/100 ✓

### Summary
- Framework: LangChain
- Trust Layer: Detected
- Articles Checked: 9, 10, 11, 12, 14, 15

### Findings (3)
- **Article 9 [HIGH]**: Missing error handling in tool calls
  - File: `src/agent.py:42` → Add try-catch around tool execution
- **Article 14 [MEDIUM]**: No input validation on external data
  - File: `src/handlers.py:18` → Validate API responses before processing

### Recommendations
Review the findings above and implement suggested fixes.

[View full report](https://airblackbox.ai/reports/...)
```

## Badge

Add this to your README to show compliance status:

```markdown
[![Compliance Score](https://img.shields.io/badge/Compliance-87%2F100-brightgreen)](https://github.com/your-org/your-repo/actions)
```

## Examples

### Scan entire `src` directory with strict mode

```yaml
- uses: airblackbox/compliance-action@v1
  with:
    python-files: './src'
    strict: true
    fail-threshold: 80
```

### Check specific articles only

```yaml
- uses: airblackbox/compliance-action@v1
  with:
    python-files: './ai_agent.py'
    articles: '9,10,14'
    fail-threshold: 75
```

### Report only, don't fail

```yaml
- uses: airblackbox/compliance-action@v1
  with:
    python-files: './src'
    strict: false
    fail-threshold: 0
```

## How It Works

1. Checks out your code
2. Runs `air-blackbox scan` on specified Python files
3. Parses compliance results
4. Posts findings as a PR comment
5. Fails the check if score is below `fail-threshold`

## Troubleshooting

**No comment posted on PR?** Check that the action has permission to write comments. GitHub Actions use `GITHUB_TOKEN` by default, which grants this permission.

**False positives?** Review findings and customize `articles` parameter to focus on relevant checks.

**Scan too slow?** Narrow `python-files` path to specific modules rather than the entire repo.

## Resources

- [air-blackbox on PyPI](https://pypi.org/project/air-blackbox/)
- [air-trust framework](https://github.com/airblackbox/air-trust)
- [airblackbox.ai documentation](https://airblackbox.ai)

## License

Apache-2.0
