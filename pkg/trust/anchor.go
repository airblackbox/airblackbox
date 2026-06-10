// External anchoring of signed checkpoints to the Rekor transparency log.
//
// Rekor (https://docs.sigstore.dev/logging/overview/) is Sigstore's public,
// append-only transparency log. Anchoring a checkpoint publishes a
// hashedrekord entry: the SHA-256 of the checkpoint payload, the Ed25519
// signature over it, and the public key. Once accepted, the entry is
// publicly fetchable and cannot be removed, so a third party can confirm
// the chain head existed at the integrated time without trusting the
// operator of this gateway.
//
// Rekor does not yet verify ML-DSA signatures, which is why checkpoints are
// dual-signed: ML-DSA-65 travels in the local evidence bundle, Ed25519 goes
// to the log.
package trust

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// DefaultRekorServer is Sigstore's public Rekor instance.
const DefaultRekorServer = "https://rekor.sigstore.dev"

// RekorAnchor is the receipt returned after a checkpoint is accepted by
// (or already present in) the transparency log.
type RekorAnchor struct {
	Server         string `json:"server"`
	UUID           string `json:"uuid"`
	LogIndex       int64  `json:"log_index"`
	IntegratedTime int64  `json:"integrated_time"` // unix seconds, per the log
	AnchoredAt     string `json:"anchored_at"`     // RFC3339, local clock
	AlreadyExisted bool   `json:"already_existed"`
}

// AnchorToRekor publishes the Ed25519 signature from a signed checkpoint to
// the given Rekor server. The checkpoint must contain an Ed25519 signature;
// it errors otherwise with an explanation.
func AnchorToRekor(server string, sc SignedCheckpoint) (RekorAnchor, error) {
	var ed *SignedData
	for i := range sc.Signatures {
		if sc.Signatures[i].Algorithm == AlgoEd25519 {
			ed = &sc.Signatures[i]
			break
		}
	}
	if ed == nil {
		return RekorAnchor{}, fmt.Errorf(
			"anchor: checkpoint has no Ed25519 signature; Rekor does not yet accept ML-DSA, create the checkpoint with both signers")
	}

	pubBytes, err := hex.DecodeString(ed.PublicKey)
	if err != nil || len(pubBytes) != ed25519.PublicKeySize {
		return RekorAnchor{}, fmt.Errorf("anchor: invalid Ed25519 public key in checkpoint")
	}
	sigBytes, err := hex.DecodeString(ed.Signature)
	if err != nil {
		return RekorAnchor{}, fmt.Errorf("anchor: invalid signature encoding: %w", err)
	}

	// Rekor wants the public key as base64-encoded PEM (PKIX).
	pkix, err := x509.MarshalPKIXPublicKey(ed25519.PublicKey(pubBytes))
	if err != nil {
		return RekorAnchor{}, fmt.Errorf("anchor: marshal public key: %w", err)
	}
	pemKey := pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: pkix})

	payload := sc.Checkpoint.PayloadBytes()
	digest := sha256.Sum256(payload)

	entry := map[string]any{
		"apiVersion": "0.0.1",
		"kind":       "hashedrekord",
		"spec": map[string]any{
			"data": map[string]any{
				"hash": map[string]any{
					"algorithm": "sha256",
					"value":     hex.EncodeToString(digest[:]),
				},
			},
			"signature": map[string]any{
				"content": base64.StdEncoding.EncodeToString(sigBytes),
				"publicKey": map[string]any{
					"content": base64.StdEncoding.EncodeToString(pemKey),
				},
			},
		},
	}
	body, _ := json.Marshal(entry)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Post(
		strings.TrimRight(server, "/")+"/api/v1/log/entries",
		"application/json", bytes.NewReader(body))
	if err != nil {
		return RekorAnchor{}, fmt.Errorf("anchor: rekor request failed: %w", err)
	}
	defer resp.Body.Close()
	respBody, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))

	switch resp.StatusCode {
	case http.StatusCreated: // 201: new entry
		anchor, err := parseRekorEntry(respBody)
		if err != nil {
			return RekorAnchor{}, err
		}
		anchor.Server = server
		anchor.AnchoredAt = time.Now().UTC().Format(time.RFC3339)
		return anchor, nil

	case http.StatusConflict: // 409: this exact entry is already in the log
		uuid := ""
		if loc := resp.Header.Get("Location"); loc != "" {
			parts := strings.Split(loc, "/")
			uuid = parts[len(parts)-1]
		}
		return RekorAnchor{
			Server:         server,
			UUID:           uuid,
			AnchoredAt:     time.Now().UTC().Format(time.RFC3339),
			AlreadyExisted: true,
		}, nil

	default:
		snippet := string(respBody)
		if len(snippet) > 300 {
			snippet = snippet[:300]
		}
		return RekorAnchor{}, fmt.Errorf("anchor: rekor returned HTTP %d: %s", resp.StatusCode, snippet)
	}
}

// parseRekorEntry extracts the UUID, log index, and integrated time from a
// Rekor create-entry response, which is a map of {uuid: {entry fields}}.
func parseRekorEntry(body []byte) (RekorAnchor, error) {
	var m map[string]struct {
		LogIndex       int64 `json:"logIndex"`
		IntegratedTime int64 `json:"integratedTime"`
	}
	if err := json.Unmarshal(body, &m); err != nil {
		return RekorAnchor{}, fmt.Errorf("anchor: parse rekor response: %w", err)
	}
	for uuid, e := range m {
		return RekorAnchor{UUID: uuid, LogIndex: e.LogIndex, IntegratedTime: e.IntegratedTime}, nil
	}
	return RekorAnchor{}, fmt.Errorf("anchor: empty rekor response")
}

// FetchRekorEntry retrieves a previously anchored entry by UUID, so anyone
// can confirm the anchor exists in the public log.
func FetchRekorEntry(server, uuid string) ([]byte, error) {
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Get(strings.TrimRight(server, "/") + "/api/v1/log/entries/" + uuid)
	if err != nil {
		return nil, fmt.Errorf("anchor: fetch entry: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("anchor: rekor returned HTTP %d for entry %s", resp.StatusCode, uuid)
	}
	return io.ReadAll(io.LimitReader(resp.Body, 1<<20))
}
