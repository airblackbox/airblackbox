// Signed chain checkpoints.
//
// A checkpoint is a canonical snapshot of the audit chain head: the chain
// length, the hash of the most recent entry, and the time it was cut.
// Checkpoints are signed with ML-DSA-65 (post-quantum) and Ed25519, so they
// can be verified locally far into the future and anchored to external
// transparency logs today.
//
// Threat model: the HMAC chain proves internal consistency, but the operator
// holds the HMAC secret and could rewrite history. A signed checkpoint that
// has been anchored externally (see anchor.go) proves the chain head existed
// at a point in time, in a log the operator does not control.
package trust

import (
	"encoding/json"
	"fmt"
	"os"
	"time"
)

// Checkpoint is the canonical payload that gets signed and anchored.
type Checkpoint struct {
	ChainLength int64  `json:"chain_length"`
	HeadHash    string `json:"head_hash"` // sha256 of the latest ChainEntry JSON
	Timestamp   string `json:"timestamp"` // RFC3339 UTC, when the checkpoint was cut
}

// PayloadBytes returns the canonical bytes that signatures cover.
// json.Marshal on a struct emits fields in declaration order, so this is
// deterministic for a given Checkpoint value.
func (c Checkpoint) PayloadBytes() []byte {
	b, _ := json.Marshal(c)
	return b
}

// SignedCheckpoint bundles a checkpoint with one or more signatures over
// its payload bytes.
type SignedCheckpoint struct {
	Checkpoint Checkpoint    `json:"checkpoint"`
	Signatures []SignedData  `json:"signatures"`
	Anchors    []RekorAnchor `json:"anchors,omitempty"`
}

// Head returns the current chain length and head hash.
// The head hash is empty when the chain has no entries.
func (ac *AuditChain) Head() (int64, string) {
	ac.mu.Lock()
	defer ac.mu.Unlock()
	return ac.seq, ac.last
}

// NewSignerEd25519 creates a Signer that uses Ed25519 regardless of ML-DSA
// availability. Rekor and most current transparency logs verify Ed25519 but
// not yet ML-DSA, so anchored checkpoints carry both signature types.
func NewSignerEd25519(keyDir string) (*Signer, error) {
	s := &Signer{keyDir: keyDir}
	if err := os.MkdirAll(keyDir, 0700); err != nil {
		return nil, fmt.Errorf("signer: create key dir: %w", err)
	}
	if err := s.loadOrGenerateEd25519(); err != nil {
		return nil, fmt.Errorf("signer: ed25519 key generation failed: %w", err)
	}
	return s, nil
}

// CreateCheckpoint cuts a checkpoint at the current chain head and signs it
// with every provided signer. At least one signer is required and the chain
// must not be empty.
func CreateCheckpoint(ac *AuditChain, signers ...*Signer) (SignedCheckpoint, error) {
	if len(signers) == 0 {
		return SignedCheckpoint{}, fmt.Errorf("checkpoint: at least one signer required")
	}
	length, head := ac.Head()
	if length == 0 {
		return SignedCheckpoint{}, fmt.Errorf("checkpoint: audit chain is empty")
	}
	cp := Checkpoint{
		ChainLength: length,
		HeadHash:    head,
		Timestamp:   time.Now().UTC().Format(time.RFC3339),
	}
	payload := cp.PayloadBytes()

	sc := SignedCheckpoint{Checkpoint: cp}
	for _, s := range signers {
		sd, err := s.Sign(payload)
		if err != nil {
			return SignedCheckpoint{}, fmt.Errorf("checkpoint: sign (%s): %w", s.Algorithm(), err)
		}
		sd.SignedAt = cp.Timestamp
		sc.Signatures = append(sc.Signatures, sd)
	}
	return sc, nil
}

// VerifySignedCheckpoint verifies every signature in the checkpoint against
// its payload bytes. It returns an error describing the first failure, or
// nil if all signatures are valid.
func VerifySignedCheckpoint(sc SignedCheckpoint) error {
	if len(sc.Signatures) == 0 {
		return fmt.Errorf("checkpoint: no signatures present")
	}
	payload := sc.Checkpoint.PayloadBytes()
	for _, sd := range sc.Signatures {
		ok, err := Verify(sd, payload)
		if err != nil {
			return fmt.Errorf("checkpoint: verify %s signature: %w", sd.Algorithm, err)
		}
		if !ok {
			return fmt.Errorf("checkpoint: %s signature is INVALID", sd.Algorithm)
		}
	}
	return nil
}

// CheckpointFromEntries cuts a checkpoint from exported chain entries, as
// returned by GET /v1/audit/export. The head hash is recomputed from the
// final entry, so it matches a checkpoint cut against the live chain.
func CheckpointFromEntries(entries []ChainEntry, signers ...*Signer) (SignedCheckpoint, error) {
	if len(signers) == 0 {
		return SignedCheckpoint{}, fmt.Errorf("checkpoint: at least one signer required")
	}
	if len(entries) == 0 {
		return SignedCheckpoint{}, fmt.Errorf("checkpoint: no chain entries")
	}
	last := entries[len(entries)-1]
	lastJSON, err := json.Marshal(last)
	if err != nil {
		return SignedCheckpoint{}, fmt.Errorf("checkpoint: marshal entry: %w", err)
	}
	cp := Checkpoint{
		ChainLength: last.Sequence,
		HeadHash:    sha256Hex(lastJSON),
		Timestamp:   time.Now().UTC().Format(time.RFC3339),
	}
	payload := cp.PayloadBytes()
	sc := SignedCheckpoint{Checkpoint: cp}
	for _, s := range signers {
		sd, err := s.Sign(payload)
		if err != nil {
			return SignedCheckpoint{}, fmt.Errorf("checkpoint: sign (%s): %w", s.Algorithm(), err)
		}
		sd.SignedAt = cp.Timestamp
		sc.Signatures = append(sc.Signatures, sd)
	}
	return sc, nil
}
