package trust

import "time"

// ControlStatus represents whether a compliance control is satisfied.
type ControlStatus string

const (
	ControlPass    ControlStatus = "pass"
	ControlFail    ControlStatus = "fail"
	ControlPartial ControlStatus = "partial"
)

// Control is a single compliance control mapped to a gateway capability.
type Control struct {
	ID             string        `json:"id"`              // e.g. "CC6.1" or "A.8.15"
	Framework      string        `json:"framework"`       // "SOC2" or "ISO27001" (ISO/IEC 27001:2022 Annex A)
	Name           string        `json:"name"`            // human-readable control name
	Description    string        `json:"description"`     // what the control requires
	Status         ControlStatus `json:"status"`          // pass, fail, or partial
	Evidence       string        `json:"evidence"`        // how the gateway satisfies this
	GatewayFeature string        `json:"gateway_feature"` // which layer provides it
}

// ComplianceReport is the result of evaluating the gateway against one or
// more compliance frameworks.
type ComplianceReport struct {
	GeneratedAt    time.Time `json:"generated_at"`
	GatewayVersion string    `json:"gateway_version"`
	Frameworks     []string  `json:"frameworks"`
	Controls       []Control `json:"controls"`
	Summary        Summary   `json:"summary"`
}

// Summary provides aggregate pass/fail counts for a compliance report.
type Summary struct {
	TotalControls int     `json:"total_controls"`
	Passing       int     `json:"passing"`
	Failing       int     `json:"failing"`
	Partial       int     `json:"partial"`
	PassRate      float64 `json:"pass_rate"`
}

// ComplianceConfig holds which frameworks to evaluate.
type ComplianceConfig struct {
	Frameworks []string `yaml:"frameworks" json:"frameworks"`
}

// EvaluateCompliance maps gateway capabilities to SOC 2 and ISO 27001 controls
// and evaluates which ones pass based on the current configuration. It
// assumes gateway authentication is on; EvaluateComplianceWithAuth says
// whether it is.
func EvaluateCompliance(cfg ComplianceConfig, chainLen int64, hasVault bool, hasGuardrails bool, hasAnalytics bool) *ComplianceReport {
	return EvaluateComplianceWithAuth(cfg, chainLen, hasVault, hasGuardrails, hasAnalytics, true)
}

// EvaluateComplianceWithAuth is EvaluateCompliance with gateway
// authentication (GATEWAY_KEY) as an input: without it, the access-control
// controls fail instead of reporting requests as authenticated.
func EvaluateComplianceWithAuth(cfg ComplianceConfig, chainLen int64, hasVault, hasGuardrails, hasAnalytics, hasAuth bool) *ComplianceReport {
	var controls []Control

	for _, fw := range cfg.Frameworks {
		switch fw {
		case "SOC2":
			controls = append(controls, evaluateSOC2(chainLen, hasVault, hasGuardrails, hasAnalytics, hasAuth)...)
		case "ISO27001":
			controls = append(controls, evaluateISO27001(chainLen, hasVault, hasGuardrails, hasAnalytics, hasAuth)...)
		}
	}

	// Compute summary.
	summary := Summary{TotalControls: len(controls)}
	for _, c := range controls {
		switch c.Status {
		case ControlPass:
			summary.Passing++
		case ControlFail:
			summary.Failing++
		case ControlPartial:
			summary.Partial++
		}
	}
	if summary.TotalControls > 0 {
		summary.PassRate = float64(summary.Passing) / float64(summary.TotalControls) * 100
	}

	return &ComplianceReport{
		GeneratedAt:    time.Now().UTC(),
		GatewayVersion: "0.7",
		Frameworks:     cfg.Frameworks,
		Controls:       controls,
		Summary:        summary,
	}
}

// evaluateSOC2 returns SOC 2 Trust Service Criteria controls mapped to gateway features.
func evaluateSOC2(chainLen int64, hasVault, hasGuardrails, hasAnalytics, hasAuth bool) []Control {
	return []Control{
		{
			ID: "CC6.1", Framework: "SOC2",
			Name:           "Logical Access Security",
			Description:    "The entity implements logical access security over protected information assets",
			Status:         boolStatus(hasAuth),
			Evidence:       conditionalEvidence(hasAuth, "Gateway authentication via the X-Gateway-Key header (GATEWAY_KEY); every endpoint but /health rejects requests without it", "GATEWAY_KEY not set — the gateway accepts unauthenticated requests"),
			GatewayFeature: "Gateway Auth",
		},
		{
			ID: "CC6.3", Framework: "SOC2",
			Name:           "Role-Based Access and Least Privilege",
			Description:    "The entity authorizes, modifies, or removes access to data based on roles",
			Status:         boolStatus(hasGuardrails),
			Evidence:       conditionalEvidence(hasGuardrails, "Prevention layer enforces tool allowlists and blocklists per policy", "Prevention layer not configured — tool access controls unavailable"),
			GatewayFeature: "Prevention Layer",
		},
		{
			ID: "CC7.2", Framework: "SOC2",
			Name:           "System Monitoring",
			Description:    "The entity monitors system components for anomalies indicative of malicious acts",
			Status:         boolStatus(hasGuardrails),
			Evidence:       conditionalEvidence(hasGuardrails, "Detection layer monitors for runaway agents: token budget, prompt loops, tool retry storms, error spirals", "Detection layer not configured — no automated monitoring"),
			GatewayFeature: "Detection Layer",
		},
		{
			ID: "CC7.3", Framework: "SOC2",
			Name:           "Change Evaluation",
			Description:    "The entity evaluates changes for impact on the system of internal control",
			Status:         boolStatus(hasVault),
			Evidence:       conditionalEvidence(hasVault, "Every AIR record includes SHA-256 checksums of request/response; vault provides immutable storage", "Vault not configured — no checksummed records"),
			GatewayFeature: "Visibility Layer",
		},
		{
			ID: "CC8.1", Framework: "SOC2",
			Name:           "Change Management",
			Description:    "The entity authorizes, designs, develops, configures, and implements changes to meet objectives",
			Status:         boolStatus(hasGuardrails),
			Evidence:       conditionalEvidence(hasGuardrails, "Prevention layer enforces policy changes: PII redaction, model limits, tool filtering, approval workflows", "Prevention layer not configured — no policy enforcement"),
			GatewayFeature: "Prevention Layer",
		},
		{
			ID: "CC4.1", Framework: "SOC2",
			Name:           "Monitoring of Controls",
			Description:    "The entity selects, develops, and performs evaluations to ascertain controls are present and functioning",
			Status:         chainStatus(chainLen),
			Evidence:       conditionalEvidence(chainLen > 0, "Cryptographic audit chain with HMAC-SHA256 signatures validates control integrity", "Audit chain empty — no records signed yet"),
			GatewayFeature: "Trust Layer",
		},
		{
			ID: "CC5.1", Framework: "SOC2",
			Name:           "Risk Assessment",
			Description:    "The entity identifies and assesses risks to the achievement of objectives",
			Status:         boolStatus(hasAnalytics),
			Evidence:       conditionalEvidence(hasAnalytics, "Optimization layer tracks per-model error rates, latency percentiles, and failure taxonomy for risk identification", "Analytics not configured — no automated risk assessment"),
			GatewayFeature: "Optimization Layer",
		},
		{
			ID: "CC7.4", Framework: "SOC2",
			Name:           "Incident Response",
			Description:    "The entity responds to identified security incidents by executing defined procedures",
			Status:         boolStatus(hasGuardrails),
			Evidence:       conditionalEvidence(hasGuardrails, "Guardrails auto-terminate runaway sessions and send webhook alerts; prevention layer blocks policy violations", "Guardrails not configured — no automated incident response"),
			GatewayFeature: "Detection Layer",
		},
		{
			ID: "CC2.1", Framework: "SOC2",
			Name:           "Information and Communication",
			Description:    "The entity internally communicates information necessary to support controls",
			Status:         ControlPass,
			Evidence:       "Gateway logs all requests with run_id, model, status, duration; OTel tracing provides distributed context",
			GatewayFeature: "Visibility Layer",
		},
		{
			ID: "A1.2", Framework: "SOC2",
			Name:           "Recovery Mechanisms",
			Description:    "The entity implements recovery mechanisms to support system availability",
			Status:         boolStatus(hasVault),
			Evidence:       conditionalEvidence(hasVault, "Replay engine (replayctl) can reconstruct any run from vault-backed AIR records", "Vault not configured — replay/recovery not available"),
			GatewayFeature: "Visibility Layer",
		},
		{
			ID: "CC6.6", Framework: "SOC2",
			Name:           "System Boundary Protection",
			Description:    "The entity implements controls to restrict access at system boundaries",
			Status:         boolStatus(hasGuardrails),
			Evidence:       conditionalEvidence(hasGuardrails, "Prevention layer acts as policy boundary: blocks unauthorized tools, redacts PII, enforces model limits", "Prevention layer not configured — no boundary controls"),
			GatewayFeature: "Prevention Layer",
		},
		{
			ID: "CC3.1", Framework: "SOC2",
			Name:           "Risk Mitigation",
			Description:    "The entity specifies objectives with sufficient clarity to enable identification of risks",
			Status:         boolStatus(hasAnalytics),
			Evidence:       conditionalEvidence(hasAnalytics, "Failure taxonomy classifies errors into 8 categories; auto-routing mitigates model failures", "Analytics not configured — no automated risk mitigation"),
			GatewayFeature: "Optimization Layer",
		},
	}
}

// evaluateISO27001 returns ISO/IEC 27001:2022 Annex A controls mapped to
// gateway features. Certification against the 2013 edition ended on
// 31 October 2025, so the IDs are the 2022 ones (ISO/IEC 27002:2022 Annex B
// maps the old numbers: 2013's A.12.4.1 and A.12.4.3 are both 2022's A.8.15).
func evaluateISO27001(chainLen int64, hasVault, hasGuardrails, hasAnalytics, hasAuth bool) []Control {
	return []Control{
		{
			ID: "A.8.15", Framework: "ISO27001",
			Name:           "Logging",
			Description:    "Logs that record activities, exceptions, faults and other relevant events shall be produced, stored, protected and analysed",
			Status:         ControlPass,
			Evidence:       "Every LLM call produces an AIR record with run_id, model, tokens, timing and status, chained with HMAC-SHA256 so a changed or deleted record is detectable; OTel traces carry the request context",
			GatewayFeature: "Visibility Layer",
		},
		{
			ID: "A.8.16", Framework: "ISO27001",
			Name:           "Monitoring Activities",
			Description:    "Networks, systems and applications shall be monitored for anomalous behaviour and appropriate actions taken",
			Status:         boolStatus(hasGuardrails),
			Evidence:       conditionalEvidence(hasGuardrails, "Detection layer watches for runaway agents: token budgets, prompt loops, tool retry storms, error spirals", "Detection layer not configured — no automated monitoring"),
			GatewayFeature: "Detection Layer",
		},
		{
			ID: "A.8.32", Framework: "ISO27001",
			Name:           "Change Management",
			Description:    "Changes to information processing facilities and information systems shall be subject to change management procedures",
			Status:         chainStatus(chainLen),
			Evidence:       conditionalEvidence(chainLen > 0, "Cryptographic audit chain ensures integrity — any modified record breaks the HMAC chain", "Audit chain empty — no cryptographic change control yet"),
			GatewayFeature: "Trust Layer",
		},
		{
			ID: "A.5.33", Framework: "ISO27001",
			Name:           "Protection of Records",
			Description:    "Records shall be protected from loss, destruction, falsification, unauthorized access and unauthorized release",
			Status:         boolStatus(hasVault),
			Evidence:       conditionalEvidence(hasVault, "Vault stores content in S3 with SHA-256 checksums; AIR records reference vault URIs", "Vault not configured — records not cryptographically protected"),
			GatewayFeature: "Visibility Layer",
		},
		{
			ID: "A.5.15", Framework: "ISO27001",
			Name:           "Access Control",
			Description:    "Rules to control physical and logical access to information and other associated assets shall be established and implemented",
			Status:         boolStatus(hasAuth),
			Evidence:       conditionalEvidence(hasAuth, "Gateway authentication via GATEWAY_KEY; guardrails config defines tool access policies in YAML", "GATEWAY_KEY not set — the gateway accepts unauthenticated requests"),
			GatewayFeature: "Gateway Auth",
		},
		{
			ID: "A.8.24", Framework: "ISO27001",
			Name:           "Use of Cryptography",
			Description:    "Rules for the effective use of cryptography, including cryptographic key management, shall be defined and implemented",
			Status:         chainStatus(chainLen),
			Evidence:       conditionalEvidence(chainLen > 0, "HMAC-SHA256 signed audit chain; SHA-256 checksums on all vault records; HMAC-signed evidence packages", "Audit chain empty — cryptographic controls not yet exercised"),
			GatewayFeature: "Trust Layer",
		},
		{
			ID: "A.5.37", Framework: "ISO27001",
			Name:           "Documented Operating Procedures",
			Description:    "Operating procedures for information processing facilities shall be documented and made available to personnel who need them",
			Status:         boolStatus(hasGuardrails),
			Evidence:       conditionalEvidence(hasGuardrails, "guardrails.yaml defines all policies declaratively; prevention and detection rules are version-controlled", "Guardrails not configured — no documented operating procedures"),
			GatewayFeature: "Detection Layer",
		},
		{
			ID: "A.6.8", Framework: "ISO27001",
			Name:           "Information Security Event Reporting",
			Description:    "Personnel shall report observed or suspected information security events through appropriate channels in a timely manner",
			Status:         boolStatus(hasGuardrails),
			Evidence:       conditionalEvidence(hasGuardrails, "Webhook alerts fire on guardrail violations; detection layer reports incidents with structured context", "Guardrails not configured — no security event reporting"),
			GatewayFeature: "Detection Layer",
		},
		{
			ID: "A.8.8", Framework: "ISO27001",
			Name:           "Management of Technical Vulnerabilities",
			Description:    "Information about technical vulnerabilities of information systems in use shall be obtained, exposure evaluated and appropriate measures taken",
			Status:         boolStatus(hasAnalytics),
			Evidence:       conditionalEvidence(hasAnalytics, "Failure taxonomy identifies 8 error categories; analytics surface model-specific vulnerability patterns", "Analytics not configured — no vulnerability assessment"),
			GatewayFeature: "Optimization Layer",
		},
		{
			// The gateway stamps UTC from the host clock; whether that clock
			// is synchronized is the host's job, so this is never a full pass.
			ID: "A.8.17", Framework: "ISO27001",
			Name:           "Clock Synchronization",
			Description:    "The clocks of information processing systems used by the organization shall be synchronized to approved time sources",
			Status:         ControlPartial,
			Evidence:       "All timestamps are UTC from the host clock (AIR records, chain entries, reports); keep the host synchronized with NTP",
			GatewayFeature: "Visibility Layer",
		},
	}
}

// Helper functions for conditional control evaluation.

func boolStatus(enabled bool) ControlStatus {
	if enabled {
		return ControlPass
	}
	return ControlFail
}

func chainStatus(chainLen int64) ControlStatus {
	if chainLen > 0 {
		return ControlPass
	}
	return ControlPartial
}

func conditionalEvidence(condition bool, pass, fail string) string {
	if condition {
		return pass
	}
	return fail
}
