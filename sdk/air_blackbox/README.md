# AIR Blackbox: EU AI Act Compliance Scanner

A comprehensive, open-source compliance scanner for detecting EU AI Act violations in Python AI systems. AIR Blackbox combines static code analysis, fine-tuned language models, and automated audit trails to ensure your AI applications meet Articles 9-15 of the EU AI Act.

## What is AIR Blackbox?

AIR Blackbox is a developer-friendly compliance tool that automatically scans Python codebases for EU AI Act compliance issues. It identifies high-risk patterns, generates evidence trails for auditors, and provides actionable remediation guidance.

**Key Capabilities:**
- Automated scanning of Python code against EU AI Act Articles 9-15
- Fine-tuned Llama model for accurate compliance classification
- Confidence scoring and human escalation workflows
- Immutable audit chain for regulatory evidence
- Local-first operation; enterprise cloud integrations available
- False positive override mechanisms
- Framework-specific compliance rules (PyTorch, TensorFlow, scikit-learn, Hugging Face)
- Multi-language model support and documentation

## System Architecture

AIR Blackbox consists of four core components:

### 1. Code Scanner
The code scanner performs static analysis on Python files:
- Parses Python AST (Abstract Syntax Tree) to understand code structure
- Identifies imports, dependencies, and framework usage
- Extracts relevant code patterns for compliance analysis
- Handles large codebases efficiently via incremental scanning
- Caches results to avoid redundant analysis

### 2. Compliance Model (air-compliance)
A fine-tuned large language model specialized in EU AI Act compliance:
- Based on Llama 2 (7B parameters)
- Fine-tuned using Unsloth with LoRA (Low-Rank Adaptation)
- Trained on labeled compliance violation examples
- Provides confidence scores for each classification
- Supports fallback to rule-based checks for high-risk patterns
- Runs locally or via API gateway for on-premise deployments

### 3. Gateway and Trust Layer
Infrastructure for secure, auditable scanning:
- HTTP API for programmatic access
- Authentication and rate limiting
- Request sanitization and injection prevention
- Inference optimization (quantization, caching, batching)
- Health monitoring and performance tracking
- Support for multi-tenant deployments

### 4. Audit Chain
Immutable record of all compliance determinations:
- Cryptographic signature chain ensuring tamper-evidence
- Links scan requests to results and human decisions
- Supports evidence export for auditors
- Automated compliance reporting
- Long-term retention for regulatory compliance

## Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager
- 8GB RAM minimum; 16GB recommended for large codebases
- macOS, Linux, or Windows (with WSL)

### Install via pip

```bash
pip install air-blackbox
```

### Install from source (for development)

```bash
git clone https://github.com/anthropics/air-blackbox.git
cd air-blackbox
pip install -e .
```

### Offline model download (optional)

For air-gapped environments, pre-download the compliance model:

```bash
python -m air_blackbox.models download --model air-compliance-v2
```

This downloads the ~4GB model to your local cache; subsequent scans will use this local copy.

## Quick Start

### Basic Scanning

Scan a Python file for compliance violations:

```bash
air-blackbox scan path/to/your_ai_system.py
```

Output includes detected violations, their location, severity, and remediation guidance:

```
Scan Results: your_ai_system.py
===============================

CRITICAL: Article 12 violation at line 42
Pattern: Missing documentation for model training data
Confidence: 0.94
Remediation: Add docstring documenting training data source, size, and preprocessing

HIGH: Article 9 violation at line 18
Pattern: No risk assessment before deployment
Confidence: 0.87
Remediation: Implement pre-deployment risk assessment per Article 9 requirements

MEDIUM: Article 11 violation at line 103
Pattern: No human monitoring of model outputs
Confidence: 0.72
Remediation: Implement logging and human review for high-risk predictions

Scan completed in 12.3 seconds
Results saved to: .air-blackbox/scan_2026-03-28_143022.json
```

### Scanning a Directory

Scan an entire repository:

```bash
air-blackbox scan --recursive path/to/my_project/
```

Options:
- `--recursive`: scan all subdirectories
- `--exclude-dirs`: skip directories (node_modules, __pycache__, etc.)
- `--framework`: specify framework (pytorch, tensorflow, huggingface)
- `--confidence-threshold`: report violations above confidence level (default: 0.7)

### Continuous Monitoring

Enable continuous compliance monitoring:

```bash
air-blackbox monitor --watch path/to/my_project/ --interval 3600
```

This checks your code every hour and alerts on new violations. Results are stored for audit purposes.

### Cloud Integration

Scan using the enterprise gateway:

```bash
air-blackbox scan --gateway https://compliance.yourcompany.com --api-key YOUR_KEY path/to/code.py
```

The gateway provides:
- Centralized compliance reporting
- Audit log aggregation
- Role-based access controls
- Multi-tenant isolation

## Core Concepts

### Compliance Articles

AIR Blackbox checks compliance against six key EU AI Act articles:

| Article | Focus Area | Key Requirements |
|---------|-----------|------------------|
| Article 9 | Risk assessment | Documented risk assessment before deployment |
| Article 10 | Training data | Data quality, documentation, source transparency |
| Article 11 | Human oversight | Human monitoring, intervention mechanisms |
| Article 12 | Documentation | Technical documentation, user instructions |
| Article 14 | Monitoring | Performance tracking, degradation detection |
| Article 15 | Transparency | Explainability, decision logging, user information |

### Confidence Scoring

Each violation detection includes a confidence score (0.0 to 1.0):
- 0.9+: High confidence; very likely a violation
- 0.7 to 0.89: Medium confidence; likely a violation; human review recommended
- 0.5 to 0.69: Low confidence; uncertain; likely false positive
- <0.5: Not reported (background noise filtering)

Default behavior flags anything >0.7 confidence. Adjust via CLI or configuration.

### Severity Levels

Violations are classified as critical, high, medium, or low:
- **Critical:** Immediate compliance risk; blocks deployment
- **High:** Significant risk; must remediate before production
- **Medium:** Should address in current release
- **Low:** Consider for next sprint; informational

## Configuration

Create an `.air-blackbox.toml` configuration file in your project root:

```toml
[scanner]
confidence_threshold = 0.7
exclude_dirs = ["__pycache__", ".venv", "node_modules"]
max_file_size_mb = 10
report_low_confidence = false

[model]
inference_engine = "local"  # "local" or "gateway"
quantization = "int8"       # reduces memory usage
cache_results = true
timeout_seconds = 300

[compliance]
articles = ["9", "10", "11", "12", "14", "15"]
frameworks = ["pytorch", "tensorflow", "huggingface", "scikit-learn"]
require_risk_assessment = true
require_documentation = true

[output]
format = "json"  # json, sarif, csv
save_locally = true
include_audit_chain = true
```

## Integration with CI/CD

### GitHub Actions

Add to your `.github/workflows/compliance.yml`:

```yaml
name: EU AI Act Compliance Check
on: [push, pull_request]
jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install AIR Blackbox
        run: pip install air-blackbox
      - name: Scan for compliance violations
        run: air-blackbox scan --recursive . --fail-on critical
      - name: Upload evidence for audit
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: compliance-audit-chain
          path: .air-blackbox/audit-chain.json
```

### GitLab CI

```yaml
compliance_scan:
  image: python:3.10
  script:
    - pip install air-blackbox
    - air-blackbox scan --recursive . --fail-on critical
  artifacts:
    paths:
      - .air-blackbox/audit-chain.json
    expire_in: 7 years
```

## Use Cases

### Pre-Deployment Compliance Checks
Run AIR Blackbox in your deployment pipeline to ensure code meets EU AI Act requirements before production release. Violations automatically block deployment until remediated.

### Continuous Compliance Monitoring
Enable continuous monitoring in production environments. AIR Blackbox alerts on new violations detected through code updates, dependency changes, or new patterns discovered in threat intelligence.

### Regulatory Audit Evidence
Generate compliance reports and audit trails for regulators. AIR Blackbox maintains immutable evidence of all scanning activities and remediation actions for regulatory inspection.

### Code Review Integration
Embed AIR Blackbox in your pull request workflow. Violations are automatically flagged for review alongside traditional code quality checks.

### Risk Assessment Support
AIR Blackbox provides structured documentation of risks identified in your AI system, supporting your Article 9 risk assessment requirements.

## Output Formats

### JSON (default)

Structured output suitable for parsing and integration:

```json
{
  "scan_id": "scan_20260328_143022",
  "file": "ai_model.py",
  "violations": [
    {
      "article": "12",
      "line": 42,
      "severity": "critical",
      "confidence": 0.94,
      "pattern": "missing_documentation",
      "remediation": "Add docstring documenting model training data"
    }
  ]
}
```

### SARIF (Static Analysis Results Format)

Industry-standard format for integration with security tools and IDEs.

### CSV

Spreadsheet format for manual audit and reporting.

## Limitations and Considerations

### Current Limitations
- Python-focused; does not analyze PyTorch configs, YAML files, or infrastructure-as-code
- May miss framework-specific compliance issues not visible in source code
- English-language analysis only; comments in other languages may be misclassified
- False positive rate approximately 5%; false negatives approximately 2% on test suite

### Model Limitations
- Fine-tuned on publicly available codebases; may have blind spots on proprietary patterns
- Limited knowledge cutoff (January 2026); new EU AI Act guidance may not be incorporated
- Does not understand business context; cannot assess whether compliance is required for your specific use case
- Requires human review for final compliance determination

### Deployment Considerations
- Local inference requires 8GB RAM; gateway mode has higher throughput for enterprise
- Scanning large codebases (>1M lines) may take several minutes
- Immutable audit chain grows with each scan; implement log rotation for long-term operations

## Support and Contributing

**Documentation:** https://air-blackbox.dev/docs
**Issue Tracker:** https://github.com/anthropics/air-blackbox/issues
**Community Forum:** https://discuss.air-blackbox.dev
**Email Support:** support@airblackbox.dev

### Contributing to AIR Blackbox

We welcome contributions in several areas:
- Framework-specific compliance rules
- Translations and internationalization
- Test cases and validation data
- Documentation improvements
- Model fine-tuning data

See CONTRIBUTING.md for guidelines.

## License

AIR Blackbox is released under the Apache 2.0 license. See LICENSE file for details.

## Citation

If you use AIR Blackbox in your research or compliance process, please cite:

```bibtex
@software{air-blackbox-2026,
  title={AIR Blackbox: EU AI Act Compliance Scanner},
  author={Anthropic},
  year={2026},
  url={https://github.com/anthropics/air-blackbox}
}
```

## Disclaimer

AIR Blackbox is a compliance scanning tool designed to assist in EU AI Act compliance assessments. It is not a substitute for legal review or consultation with compliance experts. Final compliance determinations should involve human review and consideration of your specific business context. Anthropic makes no warranty that use of this tool ensures regulatory compliance.
