# AIR Blackbox Compliance Checks

This page explains the checks reported by `air-blackbox comply --scan . -v`.
Each entry lists the mapped regulation area, what the scanner verifies, a
minimal passing example, a failing example, and the usual remediation.

The scanner combines runtime gateway evidence, static Python source analysis,
project documentation checks, GDPR checks, and conditional hiring AI checks.
Some checks only appear when the scanned project has matching context, such as
hiring or employment terms.

## EU AI Act runtime and documentation checks

| Check | Maps to | Verifies | Passing example | Failing example | Remediation |
| --- | --- | --- | --- | --- | --- |
| Risk assessment document | Article 9 | A risk assessment file exists in the scanned project. | `RISK_ASSESSMENT.md` documents risks, likelihood, impact, and mitigations. | No `RISK_ASSESSMENT.md`, `risk_assessment.md`, `risk_register.json`, or `RISK_MANAGEMENT.md`. | Add a risk assessment covering identified AI risks and mitigations. |
| Risk mitigations active | Article 9 | Runtime mitigations are enabled. | `guardrails.yaml`, vault storage, `TRUST_SIGNING_KEY`, and OTel are configured. | Gateway runs with no guardrails, vault, signing key, or OTel endpoint. | Enable guardrails, controlled storage, audit signing, and observability. |
| PII detection in prompts | Article 10 | Runtime traffic is scanned for personal data. | Requests route through the gateway or trust layer and report `0` PII findings. | No gateway/trust-layer traffic is available for PII scanning. | Start the gateway or install a trust layer and enable prompt vault redaction. |
| Data governance documentation | Article 10 | A data governance document exists. | `DATA_GOVERNANCE.md` describes data sources, consent, quality, and retention. | No `DATA_GOVERNANCE.md` or `data_governance.md`. | Add a data governance document for AI inputs and outputs. |
| Data vault (controlled storage) | Article 10 | AI records are stored in a controlled vault. | `VAULT_ENDPOINT`, `VAULT_ACCESS_KEY`, and `VAULT_SECRET_KEY` are configured. | Records are only written locally with no vault configuration. | Configure S3 or MinIO vault storage. |
| System description (README) | Article 11 | The project explains its system purpose and design. | `README.md` describes the AI system, architecture, and intended use. | The scanned directory has no `README.md`. | Add a README with purpose, architecture, and intended use. |
| Runtime system inventory (AI-BOM data) | Article 11 | Runtime model, provider, and token inventory exists. | Gateway traffic records runs, models, providers, and token counts. | `total_runs` is `0` because no AI calls have been routed through AIR. | Route AI calls through AIR or a trust layer. |
| Model card / system card | Article 11 | Model or system limitations are documented. | `MODEL_CARD.md` lists intended use, limitations, performance, and ethics. | No model card or system card exists. | Add `MODEL_CARD.md`, `model_card.md`, or `SYSTEM_CARD.md`. |
| Documentation currency | Article 11 | Runtime inventory has current traffic dates. | Recent AIR records include a `date_range_end` and active model list. | No recent runtime data exists to prove currency. | Route representative traffic before generating compliance evidence. |
| Automatic event logging | Article 12 | AI events are automatically recorded. | Gateway or trust layer records events with a date range. | Gateway is not reachable and no trust-layer logs exist. | Route AI calls through AIR. |
| Tamper-evident audit chain | Article 12 | Records are chained or signing is configured. | `TRUST_SIGNING_KEY` is set and records verify as HMAC-chain intact. | Logs exist without a signing key or intact audit chain. | Set `TRUST_SIGNING_KEY` and verify the chain. |
| Log detail and traceability | Article 12 | Records include trace fields. | Each record has `run_id`, `model`, `timestamp`, tokens, and provider. | Records are missing key trace fields. | Ensure AIR wrappers capture run, model, token, provider, and time metadata. |
| Log retention | Article 12 | Records are retained over a measurable period. | AIR records include `date_range_start` and storage location. | No retained records are available. | Keep AIR records in local or vault storage for the required period. |
| Human-in-the-loop mechanism | Article 14 | Runtime actions have evidence for human review. | High-risk actions call `air.require_approval(action)`. | Logged actions execute with no approval gate evidence. | Add approval gates for material or high-risk actions. |
| Kill switch / stop mechanism | Article 14 | A runtime stop path is available. | Gateway is reachable and guardrails are enabled. | Gateway is not running. | Start the gateway or trust layer and configure guardrails. |
| Operator understanding documentation | Article 14 | Operators have instructions and intervention guidance. | `OPERATOR_GUIDE.md` describes capabilities, limitations, and escalation. | No operator guide or runbook is present. | Add `OPERATOR_GUIDE.md`, `operator_guide.md`, or `RUNBOOK.md`. |
| Prompt injection protection | Article 15 | Runtime injection scanning is active. | Gateway scans traffic and reports no injection attempts. | No runtime injection protection is configured. | Use the gateway or trust layer for inline injection scanning. |
| Error resilience | Article 15 | Runtime error rate is within threshold. | `error_count / total_runs` is below `5%`. | Error rate is `15%` or higher. | Add retries, fallback handling, and provider failure handling. |
| API access control | Article 15 | Provider API credentials are configured. | `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set. | No provider API key is detected. | Set provider credentials securely in the environment. |
| Adversarial robustness testing | Article 15 | Red-team or adversarial test evidence exists. | `REDTEAM.md` documents adversarial tests and outcomes. | No red-team evidence exists. | Run adversarial testing and store results in `REDTEAM.md`, `redteam_results.json`, or `ADVERSARIAL_TESTING.md`. |

## Static Python source checks

| Check | Maps to | Verifies | Passing example | Failing example | Remediation |
| --- | --- | --- | --- | --- | --- |
| Python files | Scanner input | Python source is available to scan. | `air-blackbox comply --scan ./src` where `src/app.py` exists. | `air-blackbox comply --scan ./docs` with no `.py` files. | Point `--scan` at the Python AI project. |
| LLM call error handling | Article 9 | Direct LLM calls are protected by error handling. | `try: client.chat.completions.create(...) except Exception: fallback()` | `client.chat.completions.create(...)` at top level with no `try/except`. | Wrap LLM API calls in graceful error handling. |
| Fallback/recovery patterns | Article 9 | The code has fallback or recovery behavior. | `response = call_llm.with_retry()` or `default_response()` on failure. | LLM failure returns an uncaught exception to the user. | Add retry, backoff, fallback model, or default response logic. |
| Input validation / schema enforcement | Article 10 | Inputs are validated before LLM use. | `class Prompt(BaseModel): question: str` before calling the model. | Raw `request.json["prompt"]` is passed directly to the LLM. | Use Pydantic, dataclasses, JSON schema, or explicit validators. |
| PII handling in code | Article 10 | Code detects, masks, or redacts personal data. | `prompt = redact_pii(user_text)` before model invocation. | `prompt = f"Summarize {user_email} {ssn}"` with no redaction. | Add library-grade PII detection such as Presidio or scrubadub. |
| Code documentation (docstrings) | Article 11 | Public functions and classes are documented. | `def classify(text: str) -> str:\n    """Classify support request intent."""` | `def classify(text): return llm.invoke(text)` | Add docstrings to public functions and classes. |
| Type annotations | Article 11 | Public functions include type hints. | `def classify(text: str) -> str:` | `def classify(text):` | Add parameter and return type annotations. |
| Application logging | Article 12 | Application code uses structured or standard logging. | `logger.info("llm_call_completed", extra={"run_id": run_id})` | No `logging`, `structlog`, `loguru`, or `logger.info(...)` usage. | Log key AI decisions, errors, and model interactions. |
| Tracing / observability | Article 12 | AI execution can be traced across requests. | `with tracer.start_as_current_span("agent.run"):` | No trace, span, request, correlation, LangSmith, or OTel signal. | Add OpenTelemetry, LangSmith, Langfuse, or equivalent tracing. |
| Agent action audit trail | Article 12 | Agent actions, not just LLM calls, are logged. | `audit_log(user_id, action_type, target, timestamp)` | `send_email(...)` executes without action log metadata. | Record user, action type, target, timestamp, and result for each action. |
| Human-in-the-loop patterns | Article 14 | High-risk actions require human approval. | `require_approval(action="delete_record")` | Agent deletes or emails without confirmation. | Add approval gates for high-risk or irreversible operations. |
| Usage limits / budget controls | Article 14 | Operators can cap spend, tokens, or execution volume. | `cost_limit=25` or `usage_quota.enforce(user_id)` | Agent loop has no budget, RPM, token, or cost controls. | Add configurable rate, token, cost, or quota limits. |
| Agent-to-user identity binding | Article 14 | Agent actions are tied to the authorizing user. | `run_agent(auth_context={"authorized_by": user_id})` | Agent actions are logged with no user or delegation context. | Track `user_id`, `auth_context`, or `delegation_token` for actions. |
| Token scope / permission validation | Article 14 | Tokens or permissions are checked before actions. | `check_scope(token, "calendar.write")` before tool use. | Tool call uses any available token without scope checks. | Validate OAuth scopes or permissions before every delegated action. |
| Token expiry / execution bounding | Article 14 | Tokens expire and agent runs are bounded. | `if token.is_expired(): refresh_token()` and `execution_timeout=300`. | Long-running agent uses non-expiring credentials indefinitely. | Add token expiry, revocation, refresh, and execution timeouts. |
| Agent action boundaries | Article 14 | Delegated agents have explicit allowed actions or tools. | `allowed_tools=["search", "read_calendar"]` | Agent receives unrestricted tool access. | Define allowed tools, blocked actions, and policy boundaries. |
| Retry / backoff logic | Article 15 | API calls handle transient failures. | `@retry(wait=wait_exponential())` around provider calls. | Provider rate-limit error immediately fails the workflow. | Add retry and exponential backoff around network/model calls. |
| Prompt injection defense | Article 15 | Inputs are checked for injection and guardrail patterns. | `if prompt_guard.detect(user_input): block()` | User input is inserted into a system prompt without checks. | Add injection detection, content filtering, or guardrails. |
| Unsafe input handling | Article 15 | Raw user input is not interpolated directly into prompts. | `prompt = template.render(input=sanitize(user_input))` | `prompt = f"System: obey this. User: {input()}"` | Validate and sanitize user input before prompt construction. |
| LLM output validation | Article 15 | Model responses are parsed or schema-validated. | `Result.model_validate_json(response)` | `execute(response)` trusts free-form model output. | Use Pydantic, JSON schema, output parsers, or structured output. |

## Conditional hiring AI checks

These checks appear when AIR Blackbox detects hiring, recruitment, resume,
candidate, screening, or applicant-tracking context.

| Check | Maps to | Verifies | Passing example | Failing example | Remediation |
| --- | --- | --- | --- | --- | --- |
| Illinois HB 3773: ZIP code as proxy | Hiring AI law | ZIP or postal code is not used as a proxy feature in candidate scoring. | `candidate_features = {"skills": skills, "experience": years}` | `score = model.predict({"zip_code": zip_code, "resume": text})` | Remove ZIP from scoring or document disparity analysis. |
| NYC LL144: Bias audit framework | Hiring AI law | Hiring AI uses fairness metrics or bias audit tooling. | `fairlearn.metrics.demographic_parity_difference(...)` | Candidate ranking has no bias audit or disparate impact check. | Add an annual bias audit framework and fairness metrics. |
| California FEHA: Data retention | Hiring AI law | Hiring AI records have a documented retention period. | `retention_period_days = 1460` for candidate evaluation records. | Candidate scores are deleted or retained with no policy. | Add a 4-year retention policy for hiring AI decision data. |

## GDPR data protection checks

| Check | Maps to | Verifies | Passing example | Failing example | Remediation |
| --- | --- | --- | --- | --- | --- |
| GDPR consent management | GDPR Articles 6/7 | Lawful basis or consent is tracked. | `require_consent(user_id, lawful_basis="consent")` | Personal data is processed with no consent or lawful-basis field. | Add consent gates and lawful-basis tracking. |
| GDPR data minimization | GDPR Article 5(1)(c) | Only necessary data is sent to AI systems. | `payload = select_fields(user, ["role", "question"])` | Entire user profile is sent to the LLM. | Filter inputs to required fields before processing. |
| GDPR right to erasure | GDPR Article 17 | User data can be deleted or anonymized. | `delete_user_data(user_id)` removes prompt records and metadata. | No deletion path exists for personal data. | Implement erasure requests across AI logs and stores. |
| GDPR data retention policy | GDPR Article 5(1)(e) | Personal data has TTL or retention limits. | `delete_after_days = 180` for prompt records. | Prompt records are kept forever by default. | Set retention periods and cleanup jobs. |
| GDPR cross-border transfer safeguards | GDPR Articles 44-49 | Data residency and transfer controls exist. | `region="eu-west-1"` plus transfer safeguard checks. | LLM calls send EU personal data to any region without controls. | Add data residency controls and transfer safeguards. |
| GDPR data protection impact assessment | GDPR Article 35 | DPIA or privacy impact evidence exists. | `DPIA.md` documents high-risk AI processing and mitigations. | No DPIA reference for personal-data AI processing. | Document a DPIA for high-risk AI use. |
| GDPR records of processing | GDPR Article 30 | Processing activities are inventoried. | `processing_record("support_ai", purpose="ticket triage")` | No ROPA, data inventory, or processing log exists. | Maintain a register of processing activities. |
| GDPR breach notification | GDPR Articles 33/34 | Incident and breach notification paths exist. | `notify_dpa(within_hours=72)` in incident response flow. | Security incidents are logged with no notification process. | Add breach detection, incident response, and notification procedures. |

## Bias and fairness signals

The bias scanner reports findings when it sees protected-attribute references,
hardcoded decision thresholds without fairness controls, or explicit fairness
controls. These findings complement the EU AI Act and GDPR sections.

| Check | Maps to | Verifies | Passing example | Failing example | Remediation |
| --- | --- | --- | --- | --- | --- |
| Protected attribute reference review | Bias/fairness | Protected attributes are reviewed before use in AI logic. | `protected_attributes = ["age"]; fairness_report(data, protected_attributes)` | `score += 10 if candidate_age < 30 else 0` | Remove protected attributes from decisions or document fairness controls. |
| Gender reference review | Bias/fairness | Gender terms are not used as decision shortcuts. | `gender` is used only for aggregate fairness reporting. | `if gender == "female": adjust_score()` | Avoid gender-based decision logic and test for disparate impact. |
| Race or ethnicity reference review | Bias/fairness | Race and ethnicity terms are not used as decision shortcuts. | Race/ethnicity fields are used only in protected-group audit metrics. | `if race == "asian": rank += 1` | Remove race-based logic and use fairness evaluation. |
| Hardcoded threshold fairness validation | Bias/fairness | Numeric cutoffs are validated for disparate impact. | `threshold = calibrate_threshold(validation_data, fairness_metric="equalized_odds")` | `minimum_score = 0.8` with no fairness validation. | Validate thresholds against protected groups. |
| Fairness-aware controls | Bias/fairness | Bias mitigation or fairness metrics are present. | `disparate_impact_ratio = calculate_disparate_impact(results)` | No fairness, bias mitigation, parity, or calibration logic. | Add fairness metrics and mitigation before deployment. |

## Remediation workflow

1. Run `air-blackbox comply --scan . -v` on the project.
2. Fix the highest-risk failed checks first: missing audit logging, missing
   injection protection, missing human approval, and missing data controls.
3. Re-run the scanner and keep the generated evidence bundle with release or
   audit records.
4. Treat manual and hybrid checks as prompts for documentation review; AIR
   Blackbox can find evidence, but it cannot replace legal or governance review.
