package trust

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// LoadOrGenerateKey returns the signing key stored at path, generating a new
// 256-bit random key on first use. The key never leaves the local machine.
// This replaces the old hardcoded fallback key: an operator who sets no key
// still gets unforgeable signatures, at the cost of having to keep (or back
// up) the generated keyfile.
func LoadOrGenerateKey(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err == nil {
		key := strings.TrimSpace(string(data))
		if key == "" {
			return "", fmt.Errorf("trust: keyfile %s is empty", path)
		}
		return key, nil
	}
	if !os.IsNotExist(err) {
		return "", fmt.Errorf("trust: read keyfile: %w", err)
	}

	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		return "", fmt.Errorf("trust: generate key: %w", err)
	}
	key := hex.EncodeToString(raw)

	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return "", fmt.Errorf("trust: create key dir: %w", err)
	}
	if err := os.WriteFile(path, []byte(key+"\n"), 0600); err != nil {
		return "", fmt.Errorf("trust: write keyfile: %w", err)
	}
	return key, nil
}
