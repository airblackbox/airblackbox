# Contributing to AIR Blackbox

Thank you for your interest in contributing to AIR Blackbox! We welcome contributions from developers of all experience levels.

<<<<<<< Updated upstream
## Welcome

AIR Blackbox is building the standard for EU AI Act compliance scanning. Whether you are fixing a bug, adding a feature, improving documentation, or proposing new ideas, your contribution matters. We are committed to fostering an inclusive, welcoming community.

## How to Contribute

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally: `git clone https://github.com/YOUR_USERNAME/air-blackbox.git`
3. Add the upstream remote: `git remote add upstream https://github.com/jasonjshotwell/air-blackbox.git`

### Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names that summarize your change (e.g., `feature/gdpr-consent-check`, `fix/injection-detection`).

### Develop and Test

Make your changes and run tests to ensure nothing breaks:

```bash
pip install -e ".[all]"
pytest
```

Commit messages should be clear and descriptive. Reference issues when applicable.

### Submit a Pull Request

1. Push your branch to your fork: `git push origin feature/your-feature-name`
2. Open a pull request against the main repository
3. Provide a clear description of your changes and why they are needed
4. Link to related issues if applicable

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip and virtualenv

### Installation

Clone the repository and install in development mode with all dependencies:

```bash
git clone https://github.com/jasonjshotwell/air-blackbox.git
cd air-blackbox
=======
## Quick Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/gateway.git
cd gateway

# Install in dev mode with all framework extras
>>>>>>> Stashed changes
pip install -e ".[all]"

# Verify
air-blackbox --version        # Should print 1.10.0
pytest tests/ -q              # Should pass 1,500+ tests
ruff check sdk/air_blackbox/  # Should print "All checks passed!"
```

## Development Workflow

1. Create a branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run the quality checks (see below)
4. Submit a pull request

### Quality Checks (must pass before submitting)

```bash
# Lint (zero warnings required)
ruff check sdk/air_blackbox/

# Format check
ruff format sdk/air_blackbox/ --check

# Unit tests
pytest tests/ --ignore=tests/integration -q

# Integration tests (requires framework extras)
pytest tests/integration/ -q

# Coverage (must stay above 70%)
pytest tests/ --ignore=tests/integration --cov=air_blackbox --cov-fail-under=70
```

All of these run automatically in CI on every push and pull request.

## Project Structure

```
gateway/
  sdk/air_blackbox/          # The Python package (56 modules, ~13,000 LOC)
    compliance/              # EU AI Act compliance engine (Articles 9-15)
    trust/                   # Framework trust layers (LangChain, OpenAI, CrewAI, etc.)
    a2a/                     # Agent-to-agent compliance protocol
    attestation/             # ML-DSA-65 signing and attestation records
    evidence/                # Cryptographic evidence bundles
    aibom/                   # AI Bill of Materials + shadow AI detection
    injection/               # Prompt injection detection
    validate/                # Runtime validation engine
    cli.py                   # The `air-blackbox` CLI (14 commands)
  tests/                     # 1,500+ tests (74% coverage)
    integration/             # Framework integration tests (LangChain, OpenAI, CrewAI)
    conftest.py              # Shared fixtures
  .github/workflows/         # CI: lint, test matrix (Python 3.10-3.12), coverage gate
  pyproject.toml             # Package config, ruff config, coverage config
```

## Code Style

We use **ruff** for both linting and formatting. The config lives in `pyproject.toml`:

- Rules: `E`, `F`, `W`, `I` (errors, pyflakes, warnings, isort)
- Line length: 120
- Target: Python 3.10+
- isort: `air_blackbox` as first-party

Do **not** use `black` or `isort` separately. Ruff handles both. Run `ruff format sdk/air_blackbox/` to auto-format.

### Type Hints

All public functions and methods should include type hints:

```python
def scan_code(filepath: str, framework: str = "langchain") -> ComplianceResult:
    """Scan a Python file for EU AI Act compliance issues."""
    ...
```

### Docstrings

Use Google-style docstrings for all public functions, classes, and modules.

### Imports

Always use `from air_blackbox...` for imports, never `from sdk.air_blackbox...`. The `sdk/` prefix is the package source directory, not part of the import path.

## Testing

### Writing Tests

- Put unit tests in `tests/test_*.py`
- Put integration tests (requiring real framework installs) in `tests/integration/`
- Use `pytest.importorskip()` for optional framework dependencies
- Use `tmp_path` for any file I/O
- Use `unittest.mock` for network calls and external dependencies
- Target: every new module should have a corresponding test file

### Running Specific Tests

```bash
pytest tests/test_compliance.py -v          # One file
pytest tests/ -k "test_pii"                 # By keyword
pytest tests/integration/ -x --tb=short     # Integration, stop on first failure
```

## Current Priorities

We are actively working toward v1.11.0. Contributions are welcome in these areas:

1. **Test coverage**: We're at 74%. Help us reach 80%+ by testing `cli.py`, `export/pdf_report.py`, or trust layer edge cases.
2. **Documentation**: Integration guides, API reference improvements, and tutorials.
3. **New framework trust layers**: DSPy, Semantic Kernel, or other emerging agent frameworks.
4. **GDPR scanner patterns**: Additional detection rules for consent, data minimization, and erasure workflows.
5. **Injection detection**: New prompt injection patterns and evasion techniques.

Open an issue before starting major work so we can coordinate.

## Submitting a Pull Request

1. Push your branch: `git push origin feature/your-feature`
2. Open a PR against `main`
3. Fill out the PR template
4. Ensure CI passes (lint + tests + coverage gate)
5. A maintainer will review within a few days

### What makes a good PR

- Focused: one feature or fix per PR
- Tested: new code has tests, existing tests still pass
- Linted: `ruff check` and `ruff format --check` pass
- Documented: public APIs have docstrings, complex logic has comments

## Questions?

- Email: jason.j.shotwell@gmail.com
- Open a [GitHub Discussion](https://github.com/airblackbox/airblackbox/discussions)
- Check the [README](README.md) and [airblackbox.ai](https://airblackbox.ai) for docs

Thank you for helping make AI compliance accessible and standardized.
