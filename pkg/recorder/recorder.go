// Package recorder writes AIR (AI Incident Record) files — portable,
// tamper-evident audit records for every LLM interaction.
package recorder

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// Record is the AIR file format — one per LLM call.
type Record struct {
	Version          string    `json:"version"`
	RunID            string    `json:"run_id"`
	TraceID          string    `json:"trace_id"`
	Timestamp        time.Time `json:"timestamp"`
	Model            string    `json:"model"`
	Provider         string    `json:"provider"`
	Endpoint         string    `json:"endpoint"`
	RequestVaultRef  string    `json:"request_vault_ref"`
	ResponseVaultRef string    `json:"response_vault_ref"`
	RequestChecksum  string    `json:"request_checksum"`
	ResponseChecksum string    `json:"response_checksum"`
	Tokens           Tokens    `json:"tokens"`
	DurationMS       int64     `json:"duration_ms"`
	Status           string    `json:"status"`
	Error            string    `json:"error,omitempty"`
	// Trajectory linkage (additive, backward compatible). A lone call is a
	// trajectory of one step. See docs/SPEC-trajectory-chain.md.
	TrajectoryID string   `json:"trajectory_id,omitempty"`
	StepID       string   `json:"step_id,omitempty"`
	ParentIDs    []string `json:"parent_ids,omitempty"`
	// Tamper-evidence (present when the writer has chaining enabled).
	// chain_hash = HMAC-SHA256(key, prev_digest || canonical record JSON),
	// the same construction the Python SDK trust layer writes and verifies.
	ChainSeq  int64  `json:"chain_seq,omitempty"`
	ChainHash string `json:"chain_hash,omitempty"`
}

// Tokens holds token usage from the provider response.
type Tokens struct {
	Prompt     int `json:"prompt"`
	Completion int `json:"completion"`
	Total      int `json:"total"`
}

// Writer writes AIR records to a directory. With chaining enabled (see
// EnableChaining) writes are serialized and each record is linked to the
// previous one with an HMAC chain hash.
type Writer struct {
	dir string

	mu   sync.Mutex
	key  []byte // nil = chaining disabled
	prev []byte
	seq  int64
}

// NewWriter creates a writer that saves AIR files to dir.
func NewWriter(dir string) (*Writer, error) {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("recorder: create dir: %w", err)
	}
	return &Writer{dir: dir}, nil
}

// Write persists an AIR record as <run_id>.air.json.
func (w *Writer) Write(r Record) error {
	r.Version = "1.0.0"

	if w.key != nil {
		// Never trust caller-supplied chain fields; the writer owns them.
		r.ChainSeq = 0
		r.ChainHash = ""
		if err := w.writeChained(r); err != nil {
			return fmt.Errorf("recorder: write chained %s: %w", r.RunID, err)
		}
		return nil
	}

	data, err := json.MarshalIndent(r, "", "  ")
	if err != nil {
		return fmt.Errorf("recorder: marshal: %w", err)
	}

	path := filepath.Join(w.dir, r.RunID+".air.json")
	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("recorder: write %s: %w", path, err)
	}
	return nil
}

// Load reads an AIR record from a file path.
func Load(path string) (Record, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Record{}, fmt.Errorf("recorder: read %s: %w", path, err)
	}

	var r Record
	if err := json.Unmarshal(data, &r); err != nil {
		return Record{}, fmt.Errorf("recorder: parse %s: %w", path, err)
	}
	return r, nil
}
