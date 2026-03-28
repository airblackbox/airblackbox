# Contributing to AIR Blackbox Gateway

Thank you for your interest in contributing to AIR Blackbox! We welcome contributions from developers of all experience levels. This document provides guidance on how to contribute effectively.

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
pip install -e ".[all]"
```

This installs the package in editable mode with test, documentation, and development dependencies.

### Running Tests

```bash
pytest
```

For verbose output:

```bash
pytest -v
```

To run a specific test file:

```bash
pytest tests/test_compliance.py
```

## Current Priorities for v1.7.0

We are actively working on the following areas and welcome contributions:

1. Expanded GDPR patterns: Additional detection rules for consent, data minimization, and erasure workflows
2. More injection patterns: Enhanced prompt injection detection with updated ML-backed pattern refinement
3. NIST Cybersecurity Framework (CSF) mapping: Standards crosswalk documentation and compliance checks
4. Documentation improvements: Enhanced API docs, integration guides, and compliance runbooks
5. Trust layer for DSPy: Integration with the DSPy agent framework

Please open an issue if you are interested in working on any of these areas.

## Code Style and Standards

### Python Version

We require Python 3.10+. Use modern Python features and avoid legacy patterns.

### Type Hints

All functions and methods must include type hints:

```python
def scan_code(filepath: str) -> ComplianceResult:
    """Scan a Python file for EU AI Act compliance issues."""
    ...
```

### Docstrings

Use docstrings for all functions, classes, and modules. Follow Google-style docstrings:

```python
def analyze_prompt(text: str, framework: str = "langchain") -> AnalysisReport:
    """Analyze a prompt for injection patterns and compliance risks.
    
    Args:
        text: The prompt text to analyze.
        framework: The AI framework being used (langchain, crewai, etc.).
    
    Returns:
        AnalysisReport: Findings including risk level and remediation guidance.
    """
    ...
```

### Formatting

- Use 4-space indentation
- Maximum line length: 100 characters
- Run `black` and `isort` before committing
- Use meaningful variable and function names

## Contributor License Agreement

By submitting a pull request, you agree to license your contribution under the same license as this project. If your contribution is substantial, we may ask you to sign a Contributor License Agreement (CLA) to clarify rights and obligations.

The CLA ensures that:

1. You own or have the right to submit the contribution
2. Your contribution does not infringe third-party intellectual property rights
3. The project can use your contribution under its existing license
4. Your contribution is original work

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors and community members. Please see our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for our community standards and expectations.

All community members are expected to:

- Treat each other with respect and professionalism
- Welcome contributors of all backgrounds and experience levels
- Give and receive constructive feedback gracefully
- Focus on what is best for the community
- Report conduct violations to the project maintainers

## Questions or Need Help?

If you have questions about contributing, please reach out:

- Email: jason.j.shotwell@gmail.com
- Open a discussion in the GitHub Discussions tab
- Check the README and documentation for additional resources

Thank you for contributing to making AI compliance accessible and standardized across the industry.
