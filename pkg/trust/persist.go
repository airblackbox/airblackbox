package trust

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
)

// NewPersistentAuditChain creates an audit chain backed by an append-only
// JSONL file. Existing entries are loaded on startup so the chain survives
// gateway restarts, and every Append is written through to disk best-effort.
func NewPersistentAuditChain(secret, path string) (*AuditChain, error) {
	ac := NewAuditChain(secret)

	if f, err := os.Open(path); err == nil {
		scanner := bufio.NewScanner(f)
		scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
		for scanner.Scan() {
			line := scanner.Bytes()
			if len(line) == 0 {
				continue
			}
			var entry ChainEntry
			if err := json.Unmarshal(line, &entry); err != nil {
				f.Close()
				return nil, fmt.Errorf("trust: corrupt chain file %s: %w", path, err)
			}
			ac.entries = append(ac.entries, entry)
			ac.seq = entry.Sequence
			// Recompute the running hash exactly as Append does.
			entryJSON, _ := json.Marshal(entry)
			ac.last = sha256Hex(entryJSON)
		}
		f.Close()
		if err := scanner.Err(); err != nil {
			return nil, fmt.Errorf("trust: read chain file: %w", err)
		}
	} else if !os.IsNotExist(err) {
		return nil, fmt.Errorf("trust: open chain file: %w", err)
	}

	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return nil, fmt.Errorf("trust: open chain file for append: %w", err)
	}
	ac.file = f
	return ac, nil
}
