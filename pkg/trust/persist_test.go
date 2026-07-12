package trust

import (
	"path/filepath"
	"testing"
)

func TestPersistentChainSurvivesRestart(t *testing.T) {
	path := filepath.Join(t.TempDir(), "audit-chain.jsonl")

	ac1, err := NewPersistentAuditChain("test-key", path)
	if err != nil {
		t.Fatal(err)
	}
	ac1.Append("run-1", []byte(`{"run_id":"run-1"}`))
	ac1.Append("run-2", []byte(`{"run_id":"run-2"}`))

	// "Restart": reload from disk and keep appending.
	ac2, err := NewPersistentAuditChain("test-key", path)
	if err != nil {
		t.Fatal(err)
	}
	if ac2.Len() != 2 {
		t.Fatalf("reloaded chain has %d entries, want 2", ac2.Len())
	}
	ac2.Append("run-3", []byte(`{"run_id":"run-3"}`))

	valid, brokenAt, err := ac2.Verify()
	if !valid {
		t.Fatalf("cross-restart chain invalid at %d: %v", brokenAt, err)
	}

	entries := ac2.Entries()
	if len(entries) != 3 || entries[2].Sequence != 3 {
		t.Fatalf("unexpected entries after restart: len=%d lastSeq=%d", len(entries), entries[len(entries)-1].Sequence)
	}
	if entries[2].PrevHash == "" {
		t.Fatal("post-restart entry does not link to the loaded chain")
	}
}

func TestLoadOrGenerateKeyRoundTrip(t *testing.T) {
	path := filepath.Join(t.TempDir(), ".air-signing-key")

	k1, err := LoadOrGenerateKey(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(k1) != 64 {
		t.Fatalf("generated key has length %d, want 64 hex chars", len(k1))
	}
	k2, err := LoadOrGenerateKey(path)
	if err != nil {
		t.Fatal(err)
	}
	if k1 != k2 {
		t.Fatal("second load did not return the persisted key")
	}
}
