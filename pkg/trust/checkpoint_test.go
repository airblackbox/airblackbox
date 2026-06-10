package trust

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func buildChain(t *testing.T) *AuditChain {
	t.Helper()
	ac := NewAuditChain("test-secret")
	ac.Append("run-1", []byte(`{"model":"gpt-4o"}`))
	ac.Append("run-2", []byte(`{"model":"llama3.2"}`))
	ac.Append("run-3", []byte(`{"model":"claude-3-5-sonnet"}`))
	return ac
}

func TestCheckpointDualSignAndVerify(t *testing.T) {
	ac := buildChain(t)
	mldsa, err := NewSigner(t.TempDir())
	if err != nil {
		t.Fatalf("mldsa signer: %v", err)
	}
	if mldsa.Algorithm() != AlgoMLDSA65 {
		t.Fatalf("expected ML-DSA-65, got %s", mldsa.Algorithm())
	}
	ed, err := NewSignerEd25519(t.TempDir())
	if err != nil {
		t.Fatalf("ed25519 signer: %v", err)
	}

	sc, err := CreateCheckpoint(ac, mldsa, ed)
	if err != nil {
		t.Fatalf("create checkpoint: %v", err)
	}
	if sc.Checkpoint.ChainLength != 3 || sc.Checkpoint.HeadHash == "" {
		t.Fatalf("bad checkpoint: %+v", sc.Checkpoint)
	}
	if len(sc.Signatures) != 2 {
		t.Fatalf("expected 2 signatures, got %d", len(sc.Signatures))
	}
	if err := VerifySignedCheckpoint(sc); err != nil {
		t.Fatalf("verify: %v", err)
	}

	// Head hash must match an independent recomputation from entries.
	entries := ac.Entries()
	lastJSON, _ := json.Marshal(entries[len(entries)-1])
	if sc.Checkpoint.HeadHash != sha256Hex(lastJSON) {
		t.Fatal("head hash does not match recomputed last-entry hash")
	}
}

func TestCheckpointRejectsTampering(t *testing.T) {
	ac := buildChain(t)
	ed, _ := NewSignerEd25519(t.TempDir())
	sc, err := CreateCheckpoint(ac, ed)
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	sc.Checkpoint.ChainLength = 9999 // tamper
	if err := VerifySignedCheckpoint(sc); err == nil {
		t.Fatal("tampered checkpoint verified, want failure")
	}
}

func TestCheckpointEmptyChainRefused(t *testing.T) {
	ed, _ := NewSignerEd25519(t.TempDir())
	if _, err := CreateCheckpoint(NewAuditChain("s"), ed); err == nil {
		t.Fatal("expected error for empty chain")
	}
}

func TestAnchorToRekorRequestFormat(t *testing.T) {
	ac := buildChain(t)
	mldsa, _ := NewSigner(t.TempDir())
	ed, _ := NewSignerEd25519(t.TempDir())
	sc, _ := CreateCheckpoint(ac, mldsa, ed)

	var captured map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/log/entries" || r.Method != http.MethodPost {
			t.Errorf("unexpected request: %s %s", r.Method, r.URL.Path)
		}
		if err := json.NewDecoder(r.Body).Decode(&captured); err != nil {
			t.Errorf("bad body: %v", err)
		}
		w.WriteHeader(http.StatusCreated)
		w.Write([]byte(`{"24296fb24b8ad77aabc":{"logIndex":123456789,"integratedTime":1718064000}}`))
	}))
	defer srv.Close()

	anchor, err := AnchorToRekor(srv.URL, sc)
	if err != nil {
		t.Fatalf("anchor: %v", err)
	}
	if anchor.LogIndex != 123456789 || anchor.UUID != "24296fb24b8ad77aabc" {
		t.Fatalf("bad anchor receipt: %+v", anchor)
	}

	// Validate rekord shape.
	if captured["kind"] != "rekord" {
		t.Fatalf("kind = %v", captured["kind"])
	}
	spec := captured["spec"].(map[string]any)
	sig := spec["signature"].(map[string]any)
	pk := sig["publicKey"].(map[string]any)["content"].(string)
	pemDecoded, err := base64.StdEncoding.DecodeString(pk)
	if err != nil {
		t.Fatalf("base64: %v", err)
	}
	if !strings.Contains(string(pemDecoded), "BEGIN PUBLIC KEY") {
		t.Fatal("public key is not base64-encoded PEM")
	}
}

func TestAnchorRequiresEd25519(t *testing.T) {
	ac := buildChain(t)
	mldsa, _ := NewSigner(t.TempDir())
	sc, _ := CreateCheckpoint(ac, mldsa) // ML-DSA only
	if _, err := AnchorToRekor("http://unused", sc); err == nil {
		t.Fatal("expected error anchoring without Ed25519 signature")
	}
}

func TestAnchorHandles409(t *testing.T) {
	ac := buildChain(t)
	ed, _ := NewSignerEd25519(t.TempDir())
	sc, _ := CreateCheckpoint(ac, ed)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Location", "/api/v1/log/entries/deadbeef123")
		w.WriteHeader(http.StatusConflict)
	}))
	defer srv.Close()
	anchor, err := AnchorToRekor(srv.URL, sc)
	if err != nil {
		t.Fatalf("409 should not error: %v", err)
	}
	if !anchor.AlreadyExisted || anchor.UUID != "deadbeef123" {
		t.Fatalf("bad 409 handling: %+v", anchor)
	}
}
