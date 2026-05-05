package trust

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"time"
)

// EvidencePackage bundles the audit chain, compliance report, and verification
// results into a single exportable JSON document for regulators and auditors.
type EvidencePackage struct {
	ExportedAt       time.Time         `json:"exported_at"`
	GatewayID        string            `json:"gateway_id"`
	ChainLength      int64             `json:"chain_length"`
	ChainValid       bool              `json:"chain_valid"`
	ChainBrokenAt    int64             `json:"chain_broken_at,omitempty"`
	AuditEntries     []ChainEntry      `json:"audit_entries"`
	ComplianceReport *ComplianceReport `json:"compliance_report"`
	RecordCount      int64             `json:"record_count"`
	TimeRange        TimeRange         `json:"time_range"`
	Attestation      string            `json:"attestation"`                    // HMAC of package contents
	Signature        *SignedData        `json:"signature,omitempty"`            // ML-DSA-65 or Ed25519 signature
}

// TimeRange captures the earliest and latest timestamps in the audit chain.
type TimeRange struct {
	Earliest time.Time `json:"earliest"`
	Latest   time.Time `json:"latest"`
}

// GenerateEvidencePackage creates a signed evidence package from the current
// audit chain and compliance report. The package itself is signed with
// HMAC-SHA256 so regulators can verify the export hasn't been tampered with.
// If a Signer is provided, the package also gets an ML-DSA-65 (or Ed25519
// fallback) digital signature for quantum-safe verification.
func GenerateEvidencePackage(chain *AuditChain, compliance *ComplianceReport, gatewayID string, secret string, signers ...*Signer) *EvidencePackage {
	entries := chain.Entries()
	chainLen := chain.Len()

	// Verify chain integrity.
	valid, brokenAt, _ := chain.Verify()

	// Compute time range.
	tr := TimeRange{}
	if len(entries) > 0 {
		tr.Earliest = entries[0].Timestamp
		tr.Latest = entries[len(entries)-1].Timestamp
	}

	pkg := &EvidencePackage{
		ExportedAt:       time.Now().UTC(),
		GatewayID:        gatewayID,
		ChainLength:      chainLen,
		ChainValid:       valid,
		ChainBrokenAt:    brokenAt,
		AuditEntries:     entries,
		ComplianceReport: compliance,
		RecordCount:      chainLen,
		TimeRange:        tr,
		Attestation:      "", // computed below
	}

	// Sign the package with HMAC-SHA256 (attestation field is empty during signing).
	pkg.Attestation = signPackage(pkg, secret)

	// If a Signer is provided, also add an ML-DSA-65 / Ed25519 digital signature.
	if len(signers) > 0 && signers[0] != nil {
		sd, err := signers[0].SignEvidencePackage(pkg)
		if err == nil {
			pkg.Signature = &sd
		}
	}

	return pkg
}

// VerifyAttestation checks that an evidence package's attestation signature
// matches its contents. Returns true if the package hasn't been tampered with.
func VerifyAttestation(pkg *EvidencePackage, secret string) bool {
	// Save and clear the attestation for recomputation.
	savedAttestation := pkg.Attestation
	pkg.Attestation = ""
	expected := signPackage(pkg, secret)
	pkg.Attestation = savedAttestation
	return savedAttestation == expected
}

// signPackage computes the HMAC-SHA256 of the JSON-serialized package.
func signPackage(pkg *EvidencePackage, secret string) string {
	data, _ := json.Marshal(pkg)
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(data)
	return hex.EncodeToString(mac.Sum(nil))
}
