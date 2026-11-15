package trust

import (
	"encoding/json"
	"strings"
	"sync"
	"testing"
)

const testSecret = "test-signing-key-2025"

// --- Chain tests ---

func TestChainAppend(t *testing.T) {
	chain := NewAuditChain(testSecret)
	e1 := chain.Append("run-1", []byte(`{"model":"gpt-4"}`))
	e2 := chain.Append("run-2", []byte(`{"model":"gpt-4o"}`))

	if e1.Sequence != 1 {
		t.Errorf("first entry sequence = %d, want 1", e1.Sequence)
	}
	if e2.Sequence != 2 {
		t.Errorf("second entry sequence = %d, want 2", e2.Sequence)
	}
	if chain.Len() != 2 {
		t.Errorf("chain length = %d, want 2", chain.Len())
	}
}

func TestChainVerifyValid(t *testing.T) {
	chain := NewAuditChain(testSecret)
	chain.Append("run-1", []byte(`{"test":"data1"}`))
	chain.Append("run-2", []byte(`{"test":"data2"}`))
	chain.Append("run-3", []byte(`{"test":"data3"}`))

	valid, brokenAt, err := chain.Verify()
	if !valid {
		t.Errorf("valid chain reported as broken at %d: %v", brokenAt, err)
	}
}

func TestChainVerifyTampered(t *testing.T) {
	chain := NewAuditChain(testSecret)
	chain.Append("run-1", []byte(`{"test":"data1"}`))
	chain.Append("run-2", []byte(`{"test":"data2"}`))
	chain.Append("run-3", []byte(`{"test":"data3"}`))

	// Tamper with the second entry's record hash.
	chain.mu.Lock()
	chain.entries[1].RecordHash = "tampered-hash"
	chain.mu.Unlock()

	valid, brokenAt, err := chain.Verify()
	if valid {
		t.Error("tampered chain reported as valid")
	}
	if brokenAt != 2 {
		t.Errorf("brokenAt = %d, want 2", brokenAt)
	}
	if err == nil {
		t.Error("expected error for tampered chain")
	}
}

func TestChainPrevHash(t *testing.T) {
	chain := NewAuditChain(testSecret)
	chain.Append("run-1", []byte(`{"test":"first"}`))
	chain.Append("run-2", []byte(`{"test":"second"}`))

	entries := chain.Entries()

	// First entry should have empty prev_hash.
	if entries[0].PrevHash != "" {
		t.Errorf("first entry prev_hash = %q, want empty", entries[0].PrevHash)
	}
	// Second entry should have a non-empty prev_hash.
	if entries[1].PrevHash == "" {
		t.Error("second entry prev_hash is empty, want hash of first entry")
	}
}

func TestChainSignature(t *testing.T) {
	chain := NewAuditChain(testSecret)
	e1 := chain.Append("run-1", []byte(`{"test":"deterministic"}`))

	// Same input with same secret should produce the same signature.
	chain2 := NewAuditChain(testSecret)
	e2 := chain2.Append("run-1", []byte(`{"test":"deterministic"}`))

	if e1.Signature != e2.Signature {
		t.Error("same input produced different signatures")
	}

	// Different secret should produce different signature.
	chain3 := NewAuditChain("different-key")
	e3 := chain3.Append("run-1", []byte(`{"test":"deterministic"}`))

	if e1.Signature == e3.Signature {
		t.Error("different secrets produced the same signature")
	}
}

func TestChainEmpty(t *testing.T) {
	chain := NewAuditChain(testSecret)
	valid, brokenAt, err := chain.Verify()

	if !valid {
		t.Error("empty chain should be valid")
	}
	if brokenAt != 0 {
		t.Errorf("brokenAt = %d, want 0", brokenAt)
	}
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if chain.Len() != 0 {
		t.Errorf("length = %d, want 0", chain.Len())
	}
}

func TestChainConcurrent(t *testing.T) {
	chain := NewAuditChain(testSecret)
	var wg sync.WaitGroup

	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			chain.Append("run-concurrent", []byte(`{"n":`+string(rune('0'+n%10))+`}`))
		}(i)
	}
	wg.Wait()

	if chain.Len() != 50 {
		t.Errorf("chain length = %d, want 50", chain.Len())
	}

	// Chain should still verify after concurrent appends.
	valid, _, err := chain.Verify()
	if !valid {
		t.Errorf("chain invalid after concurrent appends: %v", err)
	}
}

// --- Compliance tests ---

func TestComplianceFullSetup(t *testing.T) {
	cfg := ComplianceConfig{Frameworks: []string{"SOC2", "ISO27001"}}
	report := EvaluateCompliance(cfg, 10, true, true, true)

	if report.Summary.PassRate < 90 {
		t.Errorf("full setup pass rate = %.1f%%, want >= 90%%", report.Summary.PassRate)
	}
	if report.Summary.Failing > 0 {
		t.Errorf("full setup has %d failing controls, want 0", report.Summary.Failing)
	}
}

func TestComplianceNoVault(t *testing.T) {
	cfg := ComplianceConfig{Frameworks: []string{"SOC2", "ISO27001"}}
	report := EvaluateCompliance(cfg, 10, false, true, true)

	if report.Summary.Failing == 0 {
		t.Error("no vault should cause some controls to fail")
	}
}

func TestComplianceNoGuardrails(t *testing.T) {
	cfg := ComplianceConfig{Frameworks: []string{"SOC2"}}
	report := EvaluateCompliance(cfg, 10, true, false, true)

	if report.Summary.Failing == 0 {
		t.Error("no guardrails should cause detection/prevention controls to fail")
	}
}

func TestComplianceSOC2Controls(t *testing.T) {
	cfg := ComplianceConfig{Frameworks: []string{"SOC2"}}
	report := EvaluateCompliance(cfg, 1, true, true, true)

	soc2IDs := map[string]bool{
		"CC6.1": false, "CC6.3": false, "CC7.2": false, "CC7.3": false,
		"CC8.1": false, "CC4.1": false, "CC5.1": false, "CC7.4": false,
		"CC2.1": false, "A1.2": false, "CC6.6": false, "CC3.1": false,
	}
	for _, c := range report.Controls {
		if c.Framework != "SOC2" {
			t.Errorf("non-SOC2 control in SOC2-only report: %s %s", c.Framework, c.ID)
		}
		soc2IDs[c.ID] = true
	}
	for id, found := range soc2IDs {
		if !found {
			t.Errorf("expected SOC2 control %s not found", id)
		}
	}
}

func TestComplianceISO27001Controls(t *testing.T) {
	cfg := ComplianceConfig{Frameworks: []string{"ISO27001"}}
	report := EvaluateCompliance(cfg, 1, true, true, true)

	isoIDs := map[string]bool{
		"A.8.15": false, "A.8.16": false, "A.8.32": false, "A.5.33": false,
		"A.5.15": false, "A.8.24": false, "A.5.37": false, "A.6.8": false,
		"A.8.8": false, "A.8.17": false,
	}
	for _, c := range report.Controls {
		if c.Framework != "ISO27001" {
			t.Errorf("non-ISO27001 control in ISO27001-only report: %s %s", c.Framework, c.ID)
		}
		isoIDs[c.ID] = true
	}
	for id, found := range isoIDs {
		if !found {
			t.Errorf("expected ISO27001 control %s not found", id)
		}
	}
}

// The 2013 edition's Annex A numbering is gone from the report: audits
// since 31 October 2025 are against ISO/IEC 27001:2022.
func TestComplianceISO27001UsesThe2022Numbering(t *testing.T) {
	report := EvaluateCompliance(ComplianceConfig{Frameworks: []string{"ISO27001"}}, 1, true, true, true)
	seen := map[string]bool{}
	for _, c := range report.Controls {
		for _, old := range []string{"A.9.", "A.10.", "A.12.", "A.14.", "A.16.", "A.18."} {
			if strings.HasPrefix(c.ID, old) {
				t.Errorf("control %s uses ISO 27001:2013 numbering", c.ID)
			}
		}
		if seen[c.ID] {
			t.Errorf("control %s listed twice", c.ID)
		}
		seen[c.ID] = true
	}
}

// Without GATEWAY_KEY the gateway is open, and the report must not say
// requests are authenticated.
func TestComplianceAccessControlFollowsGatewayAuth(t *testing.T) {
	cfg := ComplianceConfig{Frameworks: []string{"SOC2", "ISO27001"}}
	status := func(r *ComplianceReport, id string) ControlStatus {
		for _, c := range r.Controls {
			if c.ID == id {
				return c.Status
			}
		}
		t.Fatalf("control %s missing", id)
		return ""
	}
	open := EvaluateComplianceWithAuth(cfg, 10, true, true, true, false)
	locked := EvaluateComplianceWithAuth(cfg, 10, true, true, true, true)
	for _, id := range []string{"CC6.1", "A.5.15"} {
		if got := status(open, id); got != ControlFail {
			t.Errorf("%s without GATEWAY_KEY = %s, want fail", id, got)
		}
		if got := status(locked, id); got != ControlPass {
			t.Errorf("%s with GATEWAY_KEY = %s, want pass", id, got)
		}
	}
}

func TestComplianceSummaryMath(t *testing.T) {
	cfg := ComplianceConfig{Frameworks: []string{"SOC2", "ISO27001"}}
	report := EvaluateCompliance(cfg, 5, true, false, true)

	total := report.Summary.Passing + report.Summary.Failing + report.Summary.Partial
	if total != report.Summary.TotalControls {
		t.Errorf("pass(%d) + fail(%d) + partial(%d) = %d, want %d",
			report.Summary.Passing, report.Summary.Failing, report.Summary.Partial,
			total, report.Summary.TotalControls)
	}
}

// --- Export tests ---

func TestEvidencePackageGeneration(t *testing.T) {
	chain := NewAuditChain(testSecret)
	chain.Append("run-1", []byte(`{"model":"gpt-4"}`))
	chain.Append("run-2", []byte(`{"model":"gpt-4o"}`))

	cfg := ComplianceConfig{Frameworks: []string{"SOC2"}}
	compliance := EvaluateCompliance(cfg, chain.Len(), true, true, true)

	pkg := GenerateEvidencePackage(chain, compliance, "gw-test-001", testSecret)

	if pkg.GatewayID != "gw-test-001" {
		t.Errorf("gateway_id = %q, want gw-test-001", pkg.GatewayID)
	}
	if pkg.ChainLength != 2 {
		t.Errorf("chain_length = %d, want 2", pkg.ChainLength)
	}
	if !pkg.ChainValid {
		t.Error("chain should be valid")
	}
	if len(pkg.AuditEntries) != 2 {
		t.Errorf("audit_entries = %d, want 2", len(pkg.AuditEntries))
	}
	if pkg.ComplianceReport == nil {
		t.Error("compliance_report is nil")
	}
	if pkg.Attestation == "" {
		t.Error("attestation is empty")
	}
}

func TestEvidencePackageAttestation(t *testing.T) {
	chain := NewAuditChain(testSecret)
	chain.Append("run-1", []byte(`{"data":"test"}`))

	cfg := ComplianceConfig{Frameworks: []string{"SOC2"}}
	compliance := EvaluateCompliance(cfg, chain.Len(), true, true, true)

	pkg := GenerateEvidencePackage(chain, compliance, "gw-test", testSecret)

	if !VerifyAttestation(pkg, testSecret) {
		t.Error("attestation should verify with correct secret")
	}

	if VerifyAttestation(pkg, "wrong-secret") {
		t.Error("attestation should fail with wrong secret")
	}
}

func TestEvidencePackageTamperedAttestation(t *testing.T) {
	chain := NewAuditChain(testSecret)
	chain.Append("run-1", []byte(`{"data":"test"}`))

	cfg := ComplianceConfig{Frameworks: []string{"SOC2"}}
	compliance := EvaluateCompliance(cfg, chain.Len(), true, true, true)

	pkg := GenerateEvidencePackage(chain, compliance, "gw-test", testSecret)

	// Tamper with the package after signing.
	pkg.GatewayID = "tampered-id"

	if VerifyAttestation(pkg, testSecret) {
		t.Error("tampered package should fail attestation verification")
	}
}

func TestEvidencePackageTimeRange(t *testing.T) {
	chain := NewAuditChain(testSecret)
	chain.Append("run-1", []byte(`{"first":true}`))
	chain.Append("run-2", []byte(`{"second":true}`))
	chain.Append("run-3", []byte(`{"third":true}`))

	cfg := ComplianceConfig{Frameworks: []string{"SOC2"}}
	compliance := EvaluateCompliance(cfg, chain.Len(), true, true, true)

	pkg := GenerateEvidencePackage(chain, compliance, "gw-test", testSecret)

	if pkg.TimeRange.Earliest.IsZero() {
		t.Error("earliest timestamp is zero")
	}
	if pkg.TimeRange.Latest.IsZero() {
		t.Error("latest timestamp is zero")
	}
	if pkg.TimeRange.Latest.Before(pkg.TimeRange.Earliest) {
		t.Error("latest is before earliest")
	}
}

func TestEvidencePackageEmptyChain(t *testing.T) {
	chain := NewAuditChain(testSecret)

	cfg := ComplianceConfig{Frameworks: []string{"SOC2"}}
	compliance := EvaluateCompliance(cfg, chain.Len(), true, true, true)

	pkg := GenerateEvidencePackage(chain, compliance, "gw-empty", testSecret)

	if pkg.ChainLength != 0 {
		t.Errorf("chain_length = %d, want 0", pkg.ChainLength)
	}
	if !pkg.ChainValid {
		t.Error("empty chain should be valid")
	}
	if len(pkg.AuditEntries) != 0 {
		t.Errorf("audit_entries = %d, want 0", len(pkg.AuditEntries))
	}
}

func TestEvidencePackageJSON(t *testing.T) {
	chain := NewAuditChain(testSecret)
	chain.Append("run-1", []byte(`{"data":"json-test"}`))

	cfg := ComplianceConfig{Frameworks: []string{"SOC2"}}
	compliance := EvaluateCompliance(cfg, chain.Len(), true, true, true)

	pkg := GenerateEvidencePackage(chain, compliance, "gw-json", testSecret)

	// Should serialize to valid JSON.
	data, err := json.Marshal(pkg)
	if err != nil {
		t.Fatalf("json.Marshal failed: %v", err)
	}

	// Should deserialize back.
	var decoded EvidencePackage
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("json.Unmarshal failed: %v", err)
	}
	if decoded.GatewayID != "gw-json" {
		t.Errorf("decoded gateway_id = %q, want gw-json", decoded.GatewayID)
	}
}
