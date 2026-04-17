# air-platform

Docker Compose orchestration for the AIR Blackbox stack. Run EU AI Act compliance scanning and audit logging in one command.

## What is air-platform?

air-platform is a local development and testing environment that spins up the full AIR Blackbox compliance toolkit using Docker Compose. It bundles:

- **air-blackbox**: EU AI Act compliance scanner (Articles 9-15 checks)
- **air-trust**: Cryptographic audit chain with HMAC-SHA256 logging and Ed25519 signed handoffs
- **air-blackbox-mcp**: MCP server for Claude Desktop, Cursor, and Claude Code integration

Think of it as a self-contained sandbox for testing AI agent compliance before deployment.

## Quick Start

```bash
git clone https://github.com/airblackbox/air-platform.git
cd air-platform

# Copy and customize environment
cp .env.example .env

# Start the stack
docker-compose up -d

# Run a compliance scan
make demo

# View the dashboard
open http://localhost:8000
```

## Project Status

**Alpha** - air-platform and its components are in active development. APIs may change. Not production-ready.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
    ┌───▼─────────────────┐  ┌──▼──────────────────┐
    │  air-blackbox-mcp   │  │   air-blackbox      │
    │  (Claude Desktop)   │  │   (CLI Scanner)     │
    └───┬─────────────────┘  └──┬──────────────────┘
        │                       │
        └───────────┬───────────┘
                    │
         ┌──────────▼──────────┐
         │   air-trust Core    │
         │  HMAC + Ed25519     │
         │  Audit Chain        │
         └─────────────────────┘
                    │
         ┌──────────▼──────────┐
         │  Docker Compose     │
         │  (air-platform)     │
         └─────────────────────┘
```

## What air-trust Does

The cryptographic backbone of the stack:

- **HMAC-SHA256 Audit Chain**: Every compliance check is logged with keyed hashes for tamper detection
- **Ed25519 Signed Handoffs**: Agent actions are cryptographically signed before execution
- **Article 14 Compliance**: Implements human oversight and audit trail requirements per EU AI Act

See [air-trust on PyPI](https://pypi.org/project/air-trust/) for details.

## File Structure

```
air-platform/
├── docker-compose.yml      # Service definitions
├── Makefile                # Common tasks
├── .env.example            # Environment template
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata
├── demo.py                 # Sample compliance scan
├── dashboard.html          # Audit dashboard UI
├── docs/                   # EU AI Act mapping docs
├── tests/                  # Integration tests
└── README.md               # This file
```

## Running Demos

See what air-blackbox can scan:

```bash
# Interactive demo with compliance checks
make demo

# Run test suite
make test

# View hosted demo scenarios
open hosted-demo.html
```

## Contributing

Pull requests welcome. Please ensure tests pass:

```bash
make test
```

## Related Projects

- **[air-trust](https://github.com/airblackbox/air-trust)** - HMAC audit chains + Ed25519 signing
- **[air-blackbox](https://github.com/airblackbox/air-blackbox)** - Compliance scanner CLI
- **[air-blackbox-mcp](https://github.com/airblackbox/air-blackbox-mcp)** - Claude Desktop integration
- **[airblackbox.ai](https://airblackbox.ai)** - Project website

## License

Apache License 2.0

## Author

Jason Shotwell ([jason@airblackbox.ai](mailto:jason@airblackbox.ai))

---

**Questions?** Check the [docs/](docs/) folder or open an issue on GitHub.
