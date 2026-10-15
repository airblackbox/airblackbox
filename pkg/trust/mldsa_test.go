package trust

import (
	"encoding/hex"
	"testing"
)

// TestSignerMLDSA65RoundTrip pins the ML-DSA-65 path: the signer must come up
// post-quantum (not silently fall back to Ed25519), and a signature must
// round-trip through the package-level Verify.
func TestSignerMLDSA65RoundTrip(t *testing.T) {
	signer, err := NewSigner(t.TempDir())
	if err != nil {
		t.Fatalf("NewSigner: %v", err)
	}
	if signer.Algorithm() != AlgoMLDSA65 {
		t.Fatalf("algorithm = %s, want %s (silent Ed25519 fallback would break the post-quantum claim)",
			signer.Algorithm(), AlgoMLDSA65)
	}

	data := []byte("evidence bundle attestation payload")
	sd, err := signer.Sign(data)
	if err != nil {
		t.Fatalf("Sign: %v", err)
	}

	ok, err := Verify(sd, data)
	if err != nil {
		t.Fatalf("Verify: %v", err)
	}
	if !ok {
		t.Fatal("valid ML-DSA-65 signature failed verification")
	}
}

// TestSignerMLDSA65RejectsTampered ensures tampered data and tampered
// signatures both fail verification.
func TestSignerMLDSA65RejectsTampered(t *testing.T) {
	signer, err := NewSigner(t.TempDir())
	if err != nil {
		t.Fatalf("NewSigner: %v", err)
	}
	data := []byte("original payload")
	sd, err := signer.Sign(data)
	if err != nil {
		t.Fatalf("Sign: %v", err)
	}

	if ok, _ := Verify(sd, []byte("tampered payload")); ok {
		t.Fatal("signature verified against tampered data")
	}

	// Flip one bit rather than overwrite a byte with a constant: a signature
	// whose first byte already equals that constant (about 1 in 256) would be
	// "tampered" into itself and verify, which made this test flaky.
	tampered := sd
	tampered.Signature = flipFirstBit(t, sd.Signature)
	if tampered.Signature == sd.Signature {
		t.Fatal("tampering did not change the signature")
	}
	if ok, _ := Verify(tampered, data); ok {
		t.Fatal("tampered signature verified")
	}
}

// flipFirstBit returns the hex string with the lowest bit of its first byte
// inverted, so the result always differs from the input.
func flipFirstBit(t *testing.T, hexSig string) string {
	t.Helper()
	raw, err := hex.DecodeString(hexSig)
	if err != nil {
		t.Fatalf("decode signature: %v", err)
	}
	if len(raw) == 0 {
		t.Fatal("empty signature")
	}
	raw[0] ^= 0x01
	return hex.EncodeToString(raw)
}

// TestSignerKeyPersistence ensures a reloaded signer (same key dir) produces
// signatures verifiable alongside the original, exercising the key load path.
func TestSignerKeyPersistence(t *testing.T) {
	dir := t.TempDir()
	first, err := NewSigner(dir)
	if err != nil {
		t.Fatalf("NewSigner (first): %v", err)
	}
	data := []byte("persistent key payload")
	sd, err := first.Sign(data)
	if err != nil {
		t.Fatalf("Sign: %v", err)
	}

	second, err := NewSigner(dir)
	if err != nil {
		t.Fatalf("NewSigner (reload): %v", err)
	}
	sd2, err := second.Sign(data)
	if err != nil {
		t.Fatalf("Sign (reload): %v", err)
	}
	if sd.PublicKey != sd2.PublicKey {
		t.Fatal("reloaded signer generated a new key instead of loading the existing one")
	}
	if ok, _ := Verify(sd, data); !ok {
		t.Fatal("original signature failed after reload")
	}
}
