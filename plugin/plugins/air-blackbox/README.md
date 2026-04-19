# AIR Blackbox — Claude Code Plugin

EU AI Act compliance scanning, audit chain verification, and evidence export — inside Claude Code.

## Install

```bash
claude plugin marketplace add airblackbox/airblackbox
claude plugin install air-blackbox@air-blackbox
```

## Commands

| Command | What it does |
|---------|-------------|
| `/air-discover` | Find AI components in your project and classify their risk level |
| `/air-comply` | Run a full compliance scan (Articles 9-15, 51+ checks) |
| `/air-replay` | Replay recorded traces to detect behavioral drift |
| `/air-evidence` | Export signed evidence packages as JSON or PDF |

## Skills

The plugin includes two skills that Claude can invoke automatically:

- **compliance-scan** — Triggers when you ask about compliance, scanning, or EU AI Act requirements. Runs the scanner and explains results.
- **interpret-results** — Triggers when you have scan output and need help understanding findings, prioritizing fixes, or implementing remediation.

## Agent

- **compliance-advisor** — An EU AI Act technical advisor that maps scan findings to specific articles, prioritizes remediation by enforcement risk, and helps implement code fixes.

## Requirements

- Python 3.9+ with `pip install air-blackbox`
- For replay: Go gateway binary (`replayctl`) and MinIO vault
- For evidence export: Go binary (`evidencectl`)

## Links

- [GitHub](https://github.com/airblackbox/airblackbox)
- [Documentation](https://airblackbox.ai)
- [Interactive Demo](https://airblackbox.ai/demo/hub)

## License

Apache 2.0
