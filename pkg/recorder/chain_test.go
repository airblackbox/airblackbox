package recorder

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func chainedRecord(i int) Record {
	return Record{
		RunID:     "00000000-0000-0000-0000-00000000000" + string(rune('0'+i)),
		Timestamp: time.Date(2026, 7, 3, 0, 0, i, 0, time.UTC),
		Model:     "gpt-4",
		Provider:  "openai",
		Endpoint:  "/v1/chat/completions",
		Tokens:    Tokens{Prompt: 5, Completion: 5, Total: 10},
		Status:    "success",
	}
}

// verifyLikePython recomputes the chain exactly as the Python SDK's
// ReplayEngine.verify_chain does and reports the first break.
func verifyLikePython(t *testing.T, dir, key string) (bool, int) {
	t.Helper()
	paths, err := filepath.Glob(filepath.Join(dir, "*.air.json"))
	if err != nil {
		t.Fatal(err)
	}

	type rec struct {
		seq    int64
		clean  []byte
		stored string
	}
	var recs []rec
	for _, p := range paths {
		data, err := os.ReadFile(p)
		if err != nil {
			t.Fatal(err)
		}
		dec := json.NewDecoder(bytes.NewReader(data))
		dec.UseNumber()
		var m map[string]interface{}
		if err := dec.Decode(&m); err != nil {
			t.Fatal(err)
		}
		seqNum, ok := m["chain_seq"].(json.Number)
		if !ok {
			continue
		}
		seq, _ := seqNum.Int64()
		stored, _ := m["chain_hash"].(string)
		delete(m, "chain_hash")
		clean, err := canonicalValue(m)
		if err != nil {
			t.Fatal(err)
		}
		recs = append(recs, rec{seq: seq, clean: clean, stored: stored})
	}
	for i := range recs {
		for j := i + 1; j < len(recs); j++ {
			if recs[j].seq < recs[i].seq {
				recs[i], recs[j] = recs[j], recs[i]
			}
		}
	}

	prev := []byte(genesisPrev)
	for i, r := range recs {
		mac := hmac.New(sha256.New, []byte(key))
		mac.Write(prev)
		mac.Write(r.clean)
		sum := mac.Sum(nil)
		if r.stored != hex.EncodeToString(sum) {
			return false, i
		}
		prev = sum
	}
	return true, -1
}

func TestChainedWritesVerify(t *testing.T) {
	dir := t.TempDir()
	w, err := NewWriter(dir)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := w.EnableChaining("test-key"); err != nil {
		t.Fatal(err)
	}

	for i := 0; i < 3; i++ {
		if err := w.Write(chainedRecord(i)); err != nil {
			t.Fatal(err)
		}
	}

	ok, at := verifyLikePython(t, dir, "test-key")
	if !ok {
		t.Fatalf("untampered chain reported broken at %d", at)
	}
}

func TestChainedWriteTamperDetected(t *testing.T) {
	dir := t.TempDir()
	w, _ := NewWriter(dir)
	if _, err := w.EnableChaining("test-key"); err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 3; i++ {
		if err := w.Write(chainedRecord(i)); err != nil {
			t.Fatal(err)
		}
	}

	// Tamper with the middle record.
	path := filepath.Join(dir, chainedRecord(1).RunID+".air.json")
	data, _ := os.ReadFile(path)
	data = bytes.Replace(data, []byte(`"gpt-4"`), []byte(`"TAMPERED"`), 1)
	if err := os.WriteFile(path, data, 0644); err != nil {
		t.Fatal(err)
	}

	ok, at := verifyLikePython(t, dir, "test-key")
	if ok {
		t.Fatal("tampered chain reported intact")
	}
	if at != 1 {
		t.Fatalf("break reported at %d, want 1", at)
	}
}

func TestChainResumesAcrossRestart(t *testing.T) {
	dir := t.TempDir()

	w1, _ := NewWriter(dir)
	if _, err := w1.EnableChaining("test-key"); err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 2; i++ {
		if err := w1.Write(chainedRecord(i)); err != nil {
			t.Fatal(err)
		}
	}

	// "Restart": a fresh writer over the same directory must continue, not
	// reset, the chain.
	w2, _ := NewWriter(dir)
	resumedAt, err := w2.EnableChaining("test-key")
	if err != nil {
		t.Fatal(err)
	}
	if resumedAt != 2 {
		t.Fatalf("resumed at %d, want 2", resumedAt)
	}
	if err := w2.Write(chainedRecord(2)); err != nil {
		t.Fatal(err)
	}

	ok, at := verifyLikePython(t, dir, "test-key")
	if !ok {
		t.Fatalf("cross-restart chain reported broken at %d", at)
	}

	rec, err := Load(filepath.Join(dir, chainedRecord(2).RunID+".air.json"))
	if err != nil {
		t.Fatal(err)
	}
	if rec.ChainSeq != 3 {
		t.Fatalf("post-restart record has chain_seq %d, want 3", rec.ChainSeq)
	}
}

func TestUnchainedWriterUnchanged(t *testing.T) {
	dir := t.TempDir()
	w, _ := NewWriter(dir)
	if err := w.Write(chainedRecord(0)); err != nil {
		t.Fatal(err)
	}
	rec, err := Load(filepath.Join(dir, chainedRecord(0).RunID+".air.json"))
	if err != nil {
		t.Fatal(err)
	}
	if rec.ChainSeq != 0 || rec.ChainHash != "" {
		t.Fatalf("unchained writer produced chain fields: seq=%d hash=%q", rec.ChainSeq, rec.ChainHash)
	}
}
