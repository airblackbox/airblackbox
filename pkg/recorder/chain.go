package recorder

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strconv"
)

// genesisPrev seeds the chain, matching the Python SDK's
// trust.chain.AuditChain.GENESIS.
const genesisPrev = "genesis"

// EnableChaining turns on tamper-evident chaining for this writer. Every
// record written afterwards gets a chain_seq and a chain_hash computed as
//
//	HMAC-SHA256(key, prev_digest || canonical_json(record_without_chain_hash))
//
// which is the exact construction the Python SDK's trust layer writes and its
// replay/evidence verifiers check. If the runs directory already contains
// chained records, the chain resumes from the highest chain_seq so a gateway
// restart does not reset the chain.
//
// It returns the sequence number the chain resumed at (0 for a fresh chain).
func (w *Writer) EnableChaining(key string) (int64, error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	w.key = []byte(key)
	w.prev = []byte(genesisPrev)
	w.seq = 0
	if err := w.resumeLocked(); err != nil {
		return 0, err
	}
	return w.seq, nil
}

// resumeLocked walks existing chained records in chain_seq order and advances
// the writer's prev digest and sequence past them. It mirrors the Python
// verifier: the expected digest advances at every chained record, so a
// tampered historical record is still detectable by verification tools while
// new records continue the canonical chain.
func (w *Writer) resumeLocked() error {
	paths, err := filepath.Glob(filepath.Join(w.dir, "*.air.json"))
	if err != nil {
		return err
	}

	type chained struct {
		seq   int64
		clean []byte
	}
	var recs []chained

	for _, p := range paths {
		data, err := os.ReadFile(p)
		if err != nil {
			continue
		}
		dec := json.NewDecoder(bytes.NewReader(data))
		dec.UseNumber()
		var m map[string]interface{}
		if err := dec.Decode(&m); err != nil {
			continue
		}
		seqNum, ok := m["chain_seq"].(json.Number)
		if !ok {
			continue // unchained record: not part of the chain
		}
		seq, err := seqNum.Int64()
		if err != nil {
			continue
		}
		delete(m, "chain_hash")
		clean, err := canonicalValue(m)
		if err != nil {
			continue
		}
		recs = append(recs, chained{seq: seq, clean: clean})
	}

	sort.Slice(recs, func(i, j int) bool { return recs[i].seq < recs[j].seq })

	for _, rec := range recs {
		mac := hmac.New(sha256.New, w.key)
		mac.Write(w.prev)
		mac.Write(rec.clean)
		w.prev = mac.Sum(nil)
		w.seq = rec.seq
	}
	return nil
}

// writeChained persists a record with chain_seq and chain_hash. Must only be
// called when chaining is enabled.
func (w *Writer) writeChained(r Record) error {
	w.mu.Lock()
	defer w.mu.Unlock()

	structJSON, err := json.Marshal(r)
	if err != nil {
		return err
	}
	dec := json.NewDecoder(bytes.NewReader(structJSON))
	dec.UseNumber()
	var m map[string]interface{}
	if err := dec.Decode(&m); err != nil {
		return err
	}

	// The hash covers everything except chain_hash itself, chain_seq included.
	delete(m, "chain_hash")
	m["chain_seq"] = json.Number(strconv.FormatInt(w.seq+1, 10))

	clean, err := canonicalValue(m)
	if err != nil {
		return err
	}
	mac := hmac.New(sha256.New, w.key)
	mac.Write(w.prev)
	mac.Write(clean)
	sum := mac.Sum(nil)
	m["chain_hash"] = hex.EncodeToString(sum)

	out, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return err
	}
	path := filepath.Join(w.dir, r.RunID+".air.json")
	if err := os.WriteFile(path, out, 0644); err != nil {
		return err
	}

	// Advance chain state only after a successful write, mirroring the
	// Python writer.
	w.seq++
	w.prev = sum
	return nil
}
