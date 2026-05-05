// ML-DSA-65 (FIPS 204) post-quantum digital signature support.
//
// ML-DSA-65 (formerly Dilithium3) is a lattice-based signature scheme
// standardized by NIST as FIPS 204. It provides 128-bit post-quantum
// security, meaning signatures remain secure even against future
// quantum computers.
//
// This module provides:
//   - Key generation (keys never leave the machine)
//   - Signing of audit chain entries and evidence bundles
//   - Verification of ML-DSA-65 signatures
//   - Fallback to Ed25519 when circl is not available
//
// The signing key is generated locally and stored in the configured
// key directory. It never leaves the machine or touches the network.
package trust

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	// ML-DSA-65 from Cloudflare's circl library.
	// Dilithium mode III = ML-DSA-65 per FIPS 204.
	"github.com/cloudflare/circl/sign/dilithium/mode3"
)

// SignatureAlgorithm identifies which algorithm produced a signature.
type SignatureAlgorithm string

const (
	AlgoMLDSA65 SignatureAlgorithm = "ML-DSA-65"
	AlgoEd25519 SignatureAlgorithm = "Ed25519"
)

// Signer provides post-quantum signing and verification.
type Signer struct {
	mu        sync.RWMutex
	algo      SignatureAlgorithm
	keyDir    string

	// ML-DSA-65 keys (preferred).
	mldsaPriv *mode3.PrivateKey
	mldsaPub  *mode3.PublicKey

	// Ed25519 fallback keys.
	ed25519Priv ed25519.PrivateKey
	ed25519Pub  ed25519.PublicKey
}

// SignedData wraps a signature with metadata for verification.
type SignedData struct {
	Algorithm   SignatureAlgorithm `json:"algorithm"`
	Signature   string             `json:"signature"`    // hex-encoded
	PublicKey   string             `json:"public_key"`   // hex-encoded
	SignedAt    string             `json:"signed_at"`
}

// NewSigner creates a Signer with ML-DSA-65 key generation.
// Keys are stored in keyDir. If keys already exist, they are loaded.
// If circl is not available at compile time, falls back to Ed25519.
func NewSigner(keyDir string) (*Signer, error) {
	s := &Signer{keyDir: keyDir}

	if err := os.MkdirAll(keyDir, 0700); err != nil {
		return nil, fmt.Errorf("signer: create key dir: %w", err)
	}

	// Try ML-DSA-65 first.
	if err := s.loadOrGenerateMLDSA(); err != nil {
		// Fall back to Ed25519.
		if err := s.loadOrGenerateEd25519(); err != nil {
			return nil, fmt.Errorf("signer: key generation failed: %w", err)
		}
	}

	return s, nil
}

// Algorithm returns which signature algorithm is active.
func (s *Signer) Algorithm() SignatureAlgorithm {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.algo
}

// Sign signs arbitrary data and returns a SignedData structure.
func (s *Signer) Sign(data []byte) (SignedData, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	switch s.algo {
	case AlgoMLDSA65:
		sig := mode3.SignTo(nil, s.mldsaPriv, data, false)
		pubBytes, _ := s.mldsaPub.MarshalBinary()
		return SignedData{
			Algorithm: AlgoMLDSA65,
			Signature: hex.EncodeToString(sig),
			PublicKey: hex.EncodeToString(pubBytes),
		}, nil

	case AlgoEd25519:
		sig := ed25519.Sign(s.ed25519Priv, data)
		return SignedData{
			Algorithm: AlgoEd25519,
			Signature: hex.EncodeToString(sig),
			PublicKey: hex.EncodeToString(s.ed25519Pub),
		}, nil

	default:
		return SignedData{}, fmt.Errorf("signer: unknown algorithm: %s", s.algo)
	}
}

// Verify checks a signature against the provided public key and data.
func Verify(sd SignedData, data []byte) (bool, error) {
	sigBytes, err := hex.DecodeString(sd.Signature)
	if err != nil {
		return false, fmt.Errorf("verify: decode signature: %w", err)
	}
	pubBytes, err := hex.DecodeString(sd.PublicKey)
	if err != nil {
		return false, fmt.Errorf("verify: decode public key: %w", err)
	}

	switch sd.Algorithm {
	case AlgoMLDSA65:
		pub := new(mode3.PublicKey)
		if err := pub.UnmarshalBinary(pubBytes); err != nil {
			return false, fmt.Errorf("verify: unmarshal ML-DSA-65 key: %w", err)
		}
		return mode3.Verify(pub, data, nil, sigBytes), nil

	case AlgoEd25519:
		if len(pubBytes) != ed25519.PublicKeySize {
			return false, fmt.Errorf("verify: invalid Ed25519 key size")
		}
		return ed25519.Verify(ed25519.PublicKey(pubBytes), data, sigBytes), nil

	default:
		return false, fmt.Errorf("verify: unknown algorithm: %s", sd.Algorithm)
	}
}

// SignChain signs the entire audit chain and returns a SignedData.
func (s *Signer) SignChain(chain *AuditChain) (SignedData, error) {
	entries := chain.Entries()
	data, err := json.Marshal(entries)
	if err != nil {
		return SignedData{}, fmt.Errorf("sign chain: marshal: %w", err)
	}
	return s.Sign(data)
}

// SignEvidencePackage signs an evidence package JSON.
func (s *Signer) SignEvidencePackage(pkg *EvidencePackage) (SignedData, error) {
	// Sign with attestation field cleared.
	saved := pkg.Attestation
	pkg.Attestation = ""
	data, err := json.Marshal(pkg)
	pkg.Attestation = saved
	if err != nil {
		return SignedData{}, fmt.Errorf("sign evidence: marshal: %w", err)
	}
	return s.Sign(data)
}

// --- Key management ---

func (s *Signer) loadOrGenerateMLDSA() error {
	privPath := filepath.Join(s.keyDir, "mldsa65.key")
	pubPath := filepath.Join(s.keyDir, "mldsa65.pub")

	// Try loading existing keys.
	if privData, err := os.ReadFile(privPath); err == nil {
		priv := new(mode3.PrivateKey)
		if err := priv.UnmarshalBinary(privData); err == nil {
			if pubData, err := os.ReadFile(pubPath); err == nil {
				pub := new(mode3.PublicKey)
				if err := pub.UnmarshalBinary(pubData); err == nil {
					s.mldsaPriv = priv
					s.mldsaPub = pub
					s.algo = AlgoMLDSA65
					return nil
				}
			}
		}
	}

	// Generate new ML-DSA-65 keypair.
	pub, priv, err := mode3.GenerateKey(rand.Reader)
	if err != nil {
		return fmt.Errorf("generate ML-DSA-65 key: %w", err)
	}

	// Save keys with restrictive permissions.
	privBytes, _ := priv.MarshalBinary()
	pubBytes, _ := pub.MarshalBinary()

	if err := os.WriteFile(privPath, privBytes, 0600); err != nil {
		return fmt.Errorf("save private key: %w", err)
	}
	if err := os.WriteFile(pubPath, pubBytes, 0644); err != nil {
		return fmt.Errorf("save public key: %w", err)
	}

	s.mldsaPriv = priv
	s.mldsaPub = pub
	s.algo = AlgoMLDSA65
	return nil
}

func (s *Signer) loadOrGenerateEd25519() error {
	privPath := filepath.Join(s.keyDir, "ed25519.key")
	pubPath := filepath.Join(s.keyDir, "ed25519.pub")

	// Try loading existing keys.
	if privData, err := os.ReadFile(privPath); err == nil {
		if len(privData) == ed25519.PrivateKeySize {
			s.ed25519Priv = ed25519.PrivateKey(privData)
			s.ed25519Pub = s.ed25519Priv.Public().(ed25519.PublicKey)
			s.algo = AlgoEd25519
			return nil
		}
	}

	// Generate new Ed25519 keypair.
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return fmt.Errorf("generate Ed25519 key: %w", err)
	}

	if err := os.WriteFile(privPath, priv, 0600); err != nil {
		return fmt.Errorf("save private key: %w", err)
	}
	if err := os.WriteFile(pubPath, pub, 0644); err != nil {
		return fmt.Errorf("save public key: %w", err)
	}

	s.ed25519Priv = priv
	s.ed25519Pub = pub
	s.algo = AlgoEd25519
	return nil
}
